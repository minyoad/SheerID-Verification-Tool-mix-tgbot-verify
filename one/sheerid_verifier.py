"""SheerID 学生验证主程序"""
import re
import json
import base64
import random
import logging
import hashlib
import time
import uuid
import httpx
from typing import Dict, Optional, Tuple

from . import config
from .name_generator import NameGenerator, generate_birth_date
from .img_generator import generate_image, generate_psu_email

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_realistic_fingerprint() -> str:
    """Generate realistic browser fingerprint to avoid fraud detection (Windows)"""
    # Realistic screen resolutions
    resolutions = ["1920x1080", "2560x1440"]
    # US timezones (offset from UTC)
    timezones = [-8, -7, -6, -5, -4]  # PST, MST, CST, EST, AST
    # User agent components
    chrome_versions = ["120", "121", "122", "123", "124", "125"]
    
    components = [
        str(int(time.time() * 1000)),  # Timestamp
        str(random.random()),           # Random seed
        random.choice(resolutions),     # Screen resolution
        str(random.choice(timezones)),  # Timezone offset
        "en-US",                         # Language
        "Win32",                         # Platform - Fixed to Windows to match UA
        str(random.randint(4, 16)),     # CPU cores
        random.choice(chrome_versions), # Browser version hint
    ]
    return hashlib.md5("|".join(components).encode()).hexdigest()


class SheerIDVerifier:
    """SheerID 学生身份验证器"""

    def __init__(self, verification_id: str):
        self.verification_id = verification_id
        self.device_fingerprint = generate_realistic_fingerprint()
        # Random Chrome version for realistic User-Agent
        chrome_ver = random.choice(["120.0.6099.109", "121.0.6167.85", "122.0.6261.94", "123.0.6312.58", "124.0.6367.78"])
        major = chrome_ver.split(".")[0]
        self.user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
        # sec-ch-ua 品牌版本需与 User-Agent 主版本一致
        self._sec_ch_ua = (
            f'"Chromium";v="{major}", "Google Chrome";v="{major}", "Not-A.Brand";v="99"'
        )
        self.http_client = httpx.Client(timeout=30.0)

    def _newrelic_headers(self) -> Dict[str, str]:
        """生成 NewRelic 追踪请求头（SheerID 前端 jslib 真实请求会携带）"""
        trace_id = (uuid.uuid4().hex + uuid.uuid4().hex[:8])[:32]
        span_id = uuid.uuid4().hex[:16]
        timestamp = int(time.time() * 1000)
        payload = {
            "v": [0, 1],
            "d": {
                "ty": "Browser",
                "ac": "364029",
                "ap": "134291347",
                "id": span_id,
                "tr": trace_id,
                "ti": timestamp,
            },
        }
        return {
            "newrelic": base64.b64encode(json.dumps(payload).encode()).decode(),
            "traceparent": f"00-{trace_id}-{span_id}-01",
            "tracestate": f"364029@nr=0-1-364029-134291347-{span_id}----{timestamp}",
        }

    def __del__(self):
        if hasattr(self, "http_client"):
            self.http_client.close()

    @staticmethod
    def normalize_url(url: str) -> str:
        """规范化 URL（保留原样）"""
        return url

    @staticmethod
    def parse_verification_id(url: str) -> Optional[str]:
        match = re.search(r"verificationId=([a-f0-9]{24})", url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _sheerid_request(
        self, method: str, url: str, body: Optional[Dict] = None
    ) -> Tuple[Dict, int]:
        """发送 SheerID API 请求 - 使用浏览器风格的请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Origin": "https://services.sheerid.com",
            "Referer": f"https://services.sheerid.com/verify/{config.PROGRAM_ID}/",
            # --- 以下为 anti-detection 头（对齐真实浏览器 jslib 请求） ---
            "sec-ch-ua": self._sec_ch_ua,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "clientversion": "2.158.0",
            "clientname": "jslib",
            **self._newrelic_headers(),
        }

        try:
            response = self.http_client.request(
                method=method, url=url, json=body, headers=headers
            )
            try:
                data = response.json()
            except Exception:
                data = response.text
            return data, response.status_code
        except Exception as e:
            logger.error(f"SheerID 请求失败: {e}")
            raise

    def _upload_to_s3(self, upload_url: str, img_data: bytes) -> bool:
        """上传 PNG 到 S3"""
        try:
            headers = {"Content-Type": "image/png"}
            response = self.http_client.put(
                upload_url, content=img_data, headers=headers, timeout=60.0
            )
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error(f"S3 上传失败: {e}")
            return False

    def verify(
        self,
        first_name: str = None,
        last_name: str = None,
        email: str = None,
        birth_date: str = None,
        school_id: str = None,
    ) -> Dict:
        """执行验证流程"""
        try:
            current_step = "initial"

            if not first_name or not last_name:
                name = NameGenerator.generate()
                first_name = name["first_name"]
                last_name = name["last_name"]

            school_id = school_id or config.DEFAULT_SCHOOL_ID
            school = config.SCHOOLS[school_id]

            if not email:
                email = generate_psu_email(first_name, last_name)
            if not birth_date:
                birth_date = generate_birth_date()

            logger.info(f"学生信息: {first_name} {last_name}")
            logger.info(f"邮箱: {email}")
            logger.info(f"学校: {school['name']}")
            logger.info(f"生日: {birth_date}")
            logger.info(f"验证 ID: {self.verification_id}")

            # 生成学生证 PNG
            logger.info("步骤 1/4: 生成学生证 PNG...")
            img_data = generate_image(first_name, last_name, school_id)
            file_size = len(img_data)
            logger.info(f"✅ PNG 大小: {file_size / 1024:.2f}KB")

            # 提交学生信息
            logger.info("步骤 2/4: 提交学生信息...")

            # 获取 Turnstile 人机验证 token（SheerID 要求），并取同环境真实浏览器指纹
            from utils.captcha_solver import get_turnstile_token_with_context
            captcha_token, real_fingerprint = get_turnstile_token_with_context(
                f"{config.SHEERID_BASE_URL}/verify/{config.PROGRAM_ID}/?verificationId={self.verification_id}"
            )
            if not captcha_token:
                raise Exception(
                    "无法获取 Turnstile 人机验证 token（SheerID 要求 captchaToken 字段）。"
                    "请检查网络/代理，或配置 CAPSOLVER_API_KEY / 2CAPTCHA_API_KEY 打码服务兜底，"
                    "或设置 CAPTCHA_HEADLESS=false + xvfb 提高成功率"
                )
            # 用与 token 同环境收集的真实浏览器指纹替代随机指纹，降低风控差异
            if real_fingerprint:
                self.device_fingerprint = real_fingerprint
                logger.info(
                    f"使用真实浏览器指纹（与 token 同环境）: {real_fingerprint[:12]}..."
                )

            step2_body = {
                "firstName": first_name,
                "lastName": last_name,
                "birthDate": birth_date,
                "email": email,
                "phoneNumber": "",
                "organization": {
                    "id": int(school_id),
                    "idExtended": school["idExtended"],
                    "name": school["name"],
                },
                "deviceFingerprintHash": self.device_fingerprint,
                "locale": "en-US",
                "captchaToken": captcha_token,
                "metadata": {
                    "marketConsentValue": False,
                    "verificationId": self.verification_id,
                },
            }

            step2_data, step2_status = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectStudentPersonalInfo",
                step2_body,
            )

            if step2_status != 200:
                raise Exception(f"步骤 2 失败 (状态码 {step2_status}): {step2_data}")
            if step2_data.get("currentStep") == "error":
                error_msg = ", ".join(step2_data.get("errorIds", ["Unknown error"]))
                # 打印完整响应，便于定位具体风控规则（fraudRulesReject 时 errorIds
                # 可能附带结构化详情，如被拒字段、规则 ID 等）
                logger.error(
                    "步骤 2 完整响应: %s",
                    json.dumps(step2_data, ensure_ascii=False)[:2000],
                )
                raise Exception(f"步骤 2 错误: {error_msg}")

            logger.info(f"✅ 步骤 2 完成: {step2_data.get('currentStep')}")
            current_step = step2_data.get("currentStep", current_step)

            # 跳过 SSO（如需要）
            if current_step in ["sso", "collectStudentPersonalInfo"]:
                logger.info("步骤 3/4: 跳过 SSO 验证...")
                step3_data, _ = self._sheerid_request(
                    "DELETE",
                    f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/sso",
                )
                logger.info(f"✅ 步骤 3 完成: {step3_data.get('currentStep')}")
                current_step = step3_data.get("currentStep", current_step)

            # 上传文档并完成提交
            logger.info("步骤 4/4: 请求并上传文档...")
            step4_body = {
                "files": [
                    {"fileName": "student_card.png", "mimeType": "image/png", "fileSize": file_size}
                ]
            }
            step4_data, step4_status = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/docUpload",
                step4_body,
            )
            if not step4_data.get("documents"):
                raise Exception("未能获取上传 URL")

            upload_url = step4_data["documents"][0]["uploadUrl"]
            logger.info("✅ 获取上传 URL 成功")
            if not self._upload_to_s3(upload_url, img_data):
                raise Exception("S3 上传失败")
            logger.info("✅ 学生证上传成功")

            step6_data, _ = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/completeDocUpload",
            )
            logger.info(f"✅ 文档提交完成: {step6_data.get('currentStep')}")
            final_status = step6_data

            # 不做状态轮询，直接返回等待审核
            return {
                "success": True,
                "pending": True,
                "message": "文档已提交，等待审核",
                "verification_id": self.verification_id,
                "redirect_url": final_status.get("redirectUrl"),
                "status": final_status,
            }

        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            return {"success": False, "message": str(e), "verification_id": self.verification_id}


def main():
    """主函数 - 命令行界面"""
    import sys

    print("=" * 60)
    print("SheerID 学生身份验证工具 (Python版)")
    print("=" * 60)
    print()

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("请输入 SheerID 验证 URL: ").strip()

    if not url:
        print("❌ 错误: 未提供 URL")
        sys.exit(1)

    verification_id = SheerIDVerifier.parse_verification_id(url)
    if not verification_id:
        print("❌ 错误: 无效的验证 ID 格式")
        sys.exit(1)

    print(f"✅ 解析到验证 ID: {verification_id}")
    print()

    verifier = SheerIDVerifier(verification_id)
    result = verifier.verify()

    print()
    print("=" * 60)
    print("验证结果:")
    print("=" * 60)
    print(f"状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
    print(f"消息: {result['message']}")
    if result.get("redirect_url"):
        print(f"跳转 URL: {result['redirect_url']}")
    print("=" * 60)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
