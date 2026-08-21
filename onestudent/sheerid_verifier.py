"""
SheerID Gemini Student Verifier - API-Based Implementation

Features:
- Direct SheerID REST API calls (no browser)
- Multi-document upload (tuition receipt, transcript, ID card)
- Consistent student info via StudentInfo class
- University-specific styling
"""

import re
import logging
import asyncio
from typing import Dict, List, Optional, Tuple

import httpx

from . import config
from .name_generator import generate_name, generate_birth_date
from .student_info import StudentInfo, create_student_info
from .img_generator import generate_all_documents
from .stats import stats, select_university_weighted
from .anti_detect import get_headers, get_fingerprint, random_delay

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

# SheerID API base URL
SHEERID_API_URL = "https://services.sheerid.com/rest/v2"


class GeminiStudentVerifier:
    """Gemini Student Verification via SheerID API (Async)"""
    
    def __init__(self, verification_id: str):
        """
        Initialize verifier
        
        Args:
            verification_id: SheerID verification ID from URL
        """
        self.verification_id = verification_id
        self.organization = None
        self.fingerprint = get_fingerprint()
    
    @staticmethod
    def parse_verification_id(url: str) -> Optional[str]:
        """Extract verification ID from SheerID URL"""
        match = re.search(r"verificationId=([a-f0-9]{24})", url, re.IGNORECASE)
        if not match and "/verification/" in url:
            match = re.search(r"/verification/([a-f0-9]{24})", url, re.IGNORECASE)
        return match.group(1) if match else None
    
    async def _request(
        self, 
        client: httpx.AsyncClient, 
        method: str, 
        endpoint: str, 
        body: Dict = None
    ) -> Tuple[Dict, int]:
        """Make API request with anti-detection headers"""
        await random_delay()
        try:
            headers = get_headers()
            url = f"{SHEERID_API_URL}{endpoint}"
            
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, json=body, headers=headers)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers)
            elif method == "PUT":
                resp = await client.put(url, content=body, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            try:
                data = resp.json() if resp.text else {}
            except Exception:
                data = {"_text": resp.text}
            
            return data, resp.status_code
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def _upload_s3(
        self, 
        client: httpx.AsyncClient, 
        upload_url: str, 
        data: bytes, 
        content_type: str
    ) -> bool:
        """Upload document to S3 presigned URL"""
        try:
            resp = await client.put(
                upload_url, 
                content=data, 
                headers={"Content-Type": content_type},
                timeout=60.0
            )
            return 200 <= resp.status_code < 300
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False
    
    async def check_link(self, client: httpx.AsyncClient) -> Dict:
        """Check if verification link is valid"""
        data, status = await self._request(client, "GET", f"/verification/{self.verification_id}")
        
        if status != 200:
            return {"valid": False, "error": f"HTTP {status}"}
        
        step = data.get("currentStep", "")
        valid_steps = ["collectStudentPersonalInfo", "docUpload", "sso"]
        
        if step in valid_steps:
            return {"valid": True, "step": step}
        elif step == "success":
            return {"valid": False, "error": "Already verified"}
        elif step == "pending":
            return {"valid": False, "error": "Already pending review"}
        elif step == "error":
            error_ids = data.get("errorIds", [])
            return {"valid": False, "error": f"Error: {', '.join(error_ids)}"}
        
        return {"valid": False, "error": f"Invalid step: {step}"}
    
    async def verify(
        self,
        first_name: str = None,
        last_name: str = None,
        birth_date: str = None,
    ) -> Dict:
        """
        Execute student verification flow using API calls
        
        Features:
        - Generates consistent student info via StudentInfo class
        - Uses university-specific styling
        - Uploads ALL documents (tuition receipt, transcript, ID card)
        
        Returns:
            Dict with success status, message, and details
        """
        
        # Generate student info
        if not first_name or not last_name:
            first_name, last_name = generate_name()
        if not birth_date:
            birth_date = generate_birth_date()
        
        # Select university with styling info
        self.organization = select_university_weighted(config.UNIVERSITIES)
        
        # Create StudentInfo for consistent data across all documents
        student_info = create_student_info(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            university_config=self.organization
        )
        
        logger.info(f"Student: {student_info.full_name}")
        logger.info(f"Student ID: {student_info.student_id}")
        logger.info(f"Email: {student_info.email}")
        logger.info(f"School: {student_info.school_name}")
        logger.info(f"DOB: {birth_date}")
        logger.info(f"Verification ID: {self.verification_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Step 1: Check current status
                logger.info("Step 1/5: Checking verification status...")
                check_result = await self.check_link(client)
                
                if not check_result.get("valid"):
                    error_msg = check_result.get("error", "Unknown error")
                    logger.error(f"Link check failed: {error_msg}")
                    return {
                        "success": False,
                        "message": error_msg,
                        "verification_id": self.verification_id,
                    }
                
                current_step = check_result.get("step", "")
                logger.info(f"Current step: {current_step}")
                
                # Step 2: Submit student info (if needed)
                if current_step == "collectStudentPersonalInfo":
                    logger.info("Step 2/5: Submitting student info...")

                    # 获取 Turnstile 人机验证 token（SheerID 要求）
                    from utils.captcha_solver import get_turnstile_token
                    captcha_token = await asyncio.to_thread(
                        get_turnstile_token,
                        f"{config.SHEERID_BASE_URL}/verify/{config.PROGRAM_ID}/?verificationId={self.verification_id}"
                    )
                    if not captcha_token:
                        logger.warning("未获取到 Turnstile token，继续尝试提交")

                    body = {
                        "firstName": first_name,
                        "lastName": last_name,
                        "birthDate": birth_date,
                        "email": student_info.email,
                        "phoneNumber": "",
                        "organization": {
                            "id": self.organization["id"],
                            "idExtended": self.organization.get("idExtended", str(self.organization["id"])),
                            "name": self.organization["name"]
                        },
                        "deviceFingerprintHash": self.fingerprint,
                        "locale": "en-US",
                        "captchaToken": captcha_token,
                        "metadata": {
                            "marketConsentValue": False,
                            "verificationId": self.verification_id,
                        }
                    }
                    
                    data, status = await self._request(
                        client, "POST", 
                        f"/verification/{self.verification_id}/step/collectStudentPersonalInfo", 
                        body
                    )
                    
                    if status != 200:
                        stats.record(self.organization["name"], False)
                        return {
                            "success": False,
                            "message": f"Submit failed: HTTP {status}",
                            "verification_id": self.verification_id,
                        }
                    
                    if data.get("currentStep") == "error":
                        error_ids = data.get("errorIds", [])
                        stats.record(self.organization["name"], False)
                        return {
                            "success": False,
                            "message": f"Error: {', '.join(error_ids)}",
                            "verification_id": self.verification_id,
                        }
                    
                    current_step = data.get("currentStep", "")
                    logger.info(f"After submit, step: {current_step}")
                else:
                    logger.info("Step 2/5: Skipping (already past info submission)")
                
                # Step 3: Skip SSO if needed
                if current_step == "sso":
                    logger.info("Step 3/5: Skipping SSO...")
                    await self._request(client, "DELETE", f"/verification/{self.verification_id}/step/sso")
                else:
                    logger.info("Step 3/5: No SSO step")
                
                # Step 4: Generate and upload ALL documents
                logger.info("Step 4/5: Generating ALL documents with consistent info...")
                
                documents = generate_all_documents(student_info)
                logger.info(f"Generated {len(documents)} documents:")
                for doc_bytes, filename, mime_type in documents:
                    logger.info(f"  - {filename}: {len(doc_bytes)/1024:.1f} KB ({mime_type})")
                
                # Request upload URLs for ALL documents
                files_list = [
                    {
                        "fileName": filename,
                        "mimeType": mime_type,
                        "fileSize": len(doc_bytes)
                    }
                    for doc_bytes, filename, mime_type in documents
                ]
                
                upload_body = {"files": files_list}
                
                logger.info(f"Requesting upload URLs for {len(files_list)} files...")
                data, status = await self._request(
                    client, "POST",
                    f"/verification/{self.verification_id}/step/docUpload",
                    upload_body
                )
                
                if not data.get("documents"):
                    stats.record(self.organization["name"], False)
                    return {
                        "success": False,
                        "message": "No upload URLs received",
                        "verification_id": self.verification_id,
                    }
                
                # Upload each document to its S3 URL
                upload_urls = data["documents"]
                logger.info(f"Received {len(upload_urls)} upload URLs")
                
                for i, (doc_bytes, filename, mime_type) in enumerate(documents):
                    if i >= len(upload_urls):
                        logger.warning(f"No upload URL for document {i+1}: {filename}")
                        continue
                    
                    upload_url = upload_urls[i].get("uploadUrl")
                    if not upload_url:
                        logger.warning(f"Invalid upload URL for: {filename}")
                        continue
                    
                    logger.info(f"Uploading {filename}...")
                    if not await self._upload_s3(client, upload_url, doc_bytes, mime_type):
                        logger.error(f"Failed to upload: {filename}")
                        # Continue with other uploads even if one fails
                    else:
                        logger.info(f"  ✓ Uploaded: {filename}")
                
                # Step 5: Complete upload
                logger.info("Step 5/5: Completing upload...")
                data, status = await self._request(
                    client, "POST",
                    f"/verification/{self.verification_id}/step/completeDocUpload"
                )
                
                final_step = data.get("currentStep", "pending")
                redirect_url = data.get("redirectUrl", "")
                
                logger.info(f"Final step: {final_step}")
                stats.record(self.organization["name"], True)
                
                return {
                    "success": True,
                    "pending": final_step in ["pending", "docReview"],
                    "message": "Verification submitted successfully",
                    "student": student_info.full_name,
                    "email": student_info.email,
                    "student_id": student_info.student_id,
                    "school": student_info.school_name,
                    "doc_count": len(documents),
                    "doc_types": ", ".join([f[1] for f in documents]),
                    "redirect_url": redirect_url,
                    "verification_id": self.verification_id,
                }
                
            except Exception as e:
                logger.error(f"Verification failed: {e}")
                if self.organization:
                    stats.record(self.organization["name"], False)
                return {
                    "success": False,
                    "message": str(e),
                    "verification_id": self.verification_id,
                }
