"""PNG 学生证生成模块 - Multi-University & Multi-Document Type Support

Supports:
- Multiple document types: Class Schedule, Tuition Receipt, Enrollment Verification
- Multiple universities: MIT, Stanford, Berkeley, CMU, Columbia, NYU, UMich, Georgia Tech
- Realistic screenshot effects: noise, blur, randomization
"""
import random
import sys
import os
from datetime import datetime
from io import BytesIO

# Add parent directory to path for utils imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.document_templates import (
    DocumentType,
    get_random_university,
    generate_university_id,
    generate_university_email,
    get_random_major,
    get_random_term,
    get_random_courses,
    get_random_tuition_amount,
    get_tuition_breakdown,
    get_academic_year,
)
from utils.image_effects import (
    apply_all_effects,
    randomize_viewport,
    get_random_zoom,
)


def generate_class_schedule_html(first_name: str, last_name: str, university_key: str, university_config: dict) -> str:
    """Generate Class Schedule HTML for a university"""
    student_id = generate_university_id(university_key)
    email= generate_university_email(first_name, last_name, university_key)
    name = f"{first_name} {last_name}"
    date = datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')
    major = get_random_major()
    term, term_dates = get_random_term()
    courses = get_random_courses(count=random.randint(4, 6))
    
    primary_color = university_config['primary_color']
    secondary_color = university_config.get('secondary_color', '#6c757d')
    uni_name = university_config['name']
    system_name = university_config['system_name']
    logo_text = university_config['logo_text']
    
    # Generate course rows
    course_rows = ""
    for course in courses:
        course_rows += f"""
                <tr>
                    <td>{course['class_number']}</td>
                    <td class="course-code">{course['code']}</td>
                    <td class="course-title">{course['title']}</td>
                    <td>{course['time']}</td>
                    <td>{course['room']}</td>
                    <td>{course['units']}.00</td>
                </tr>"""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{system_name} - Student Schedule</title>
    <style>
        :root {{
            --primary-color: {primary_color};
            --secondary-color: {secondary_color};
            --bg-gray: #f4f4f4;
            --text-color: #333;
        }}

        body {{
            font-family: "Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif;
            background-color: #e0e0e0;
            margin: 0;
            padding: 20px;
            color: var(--text-color);
            display: flex;
            justify-content: center;
        }}

        .viewport {{
            width: 100%;
            max-width: 1100px;
            background-color: #fff;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            min-height: 800px;
            display: flex;
            flex-direction: column;
        }}

        .header {{
            background-color: var(--primary-color);
            color: white;
            padding: 0 20px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .logo {{
            font-family: "Georgia", serif;
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 1px;
            border-right: 1px solid rgba(255,255,255,0.3);
            padding-right: 15px;
        }}

        .system-name {{
            font-size: 18px;
            font-weight: 300;
        }}

        .user-menu {{
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 20px;
        }}

        .nav-bar {{
            background-color: #f8f8f8;
            border-bottom: 1px solid #ddd;
            padding: 10px 20px;
            font-size: 13px;
            color: #666;
            display: flex;
            gap: 20px;
        }}
        .nav-item {{ cursor: pointer; }}
        .nav-item.active {{ color: var(--primary-color); font-weight: bold; border-bottom: 2px solid var(--primary-color); padding-bottom: 8px; }}

        .content {{
            padding: 30px;
            flex: 1;
        }}

        .page-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 20px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}

        .page-title {{
            font-size: 24px;
            color: var(--primary-color);
            margin: 0;
        }}

        .term-selector {{
            background: #fff;
            border: 1px solid #ccc;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 14px;
            color: #333;
            font-weight: bold;
        }}

        .student-card {{
            background: #fcfcfc;
            border: 1px solid #e0e0e0;
            padding: 15px;
            margin-bottom: 25px;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            font-size: 13px;
        }}
        .info-label {{ color: #777; font-size: 11px; text-transform: uppercase; margin-bottom: 4px; }}
        .info-val {{ font-weight: bold; color: #333; font-size: 14px; }}
        .status-badge {{
            background-color: #e6fffa; color: #007a5e;
            padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #b2f5ea;
        }}

        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        .schedule-table th {{
            text-align: left;
            padding: 12px;
            background-color: #f0f0f0;
            border-bottom: 2px solid #ccc;
            color: #555;
        }}

        .schedule-table td {{
            padding: 15px 12px;
            border-bottom: 1px solid #eee;
        }}

        .course-code {{ font-weight: bold; color: var(--primary-color); }}
        .course-title {{ font-weight: 500; }}

        @media print {{
            body {{ background: white; padding: 0; }}
            .viewport {{ box-shadow: none; max-width: 100%; min-height: auto; }}
            .nav-bar {{ display: none; }}
            @page {{ margin: 1cm; size: landscape; }}
        }}
    </style>
</head>
<body>

<div class="viewport">
    <div class="header">
        <div class="brand">
            <div class="logo">{logo_text}</div>
            <div class="system-name">{system_name}</div>
        </div>
        <div class="user-menu">
            <span>Welcome, <strong>{name}</strong></span>
            <span>|</span>
            <span>Sign Out</span>
        </div>
    </div>

    <div class="nav-bar">
        <div class="nav-item">Student Home</div>
        <div class="nav-item active">My Class Schedule</div>
        <div class="nav-item">Academics</div>
        <div class="nav-item">Finances</div>
        <div class="nav-item">Campus Life</div>
    </div>

    <div class="content">
        <div class="page-header">
            <h1 class="page-title">My Class Schedule</h1>
            <div class="term-selector">
                Term: <strong>{term}</strong> ({term_dates})
            </div>
        </div>

        <div class="student-card">
            <div>
                <div class="info-label">Student Name</div>
                <div class="info-val">{name}</div>
            </div>
            <div>
                <div class="info-label">Student ID</div>
                <div class="info-val">{student_id}</div>
            </div>
            <div>
                <div class="info-label">Academic Program</div>
                <div class="info-val">{major}</div>
            </div>
            <div>
                <div class="info-label">Enrollment Status</div>
                <div class="status-badge">✅ Enrolled</div>
            </div>
        </div>

        <div style="margin-bottom: 10px; font-size: 12px; color: #666; text-align: right;">
            Data retrieved: <span>{date}</span>
        </div>

        <table class="schedule-table">
            <thead>
                <tr>
                    <th width="10%">Class Nbr</th>
                    <th width="15%">Course</th>
                    <th width="35%">Title</th>
                    <th width="20%">Days & Times</th>
                    <th width="10%">Room</th>
                    <th width="10%">Units</th>
                </tr>
            </thead>
            <tbody>{course_rows}
            </tbody>
        </table>

        <div style="margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px; font-size: 11px; color: #888; text-align: center;">
            &copy; 2025 {uni_name}. All rights reserved.<br>
            {system_name} is the student information system.
        </div>
    </div>
</div>

</body>
</html>
"""
    
    return html


def generate_tuition_receipt_html(first_name: str, last_name: str, university_key: str, university_config: dict) -> str:
    """Generate Tuition Receipt HTML for a university with detailed fee breakdown"""
    student_id = generate_university_id(university_key)
    name = f"{first_name} {last_name}"
    date = datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')
    major = get_random_major()
    term, term_dates = get_random_term()
    academic_year = get_academic_year()
    
    # Get detailed tuition breakdown
    tuition_items = get_tuition_breakdown()
    total_amount = sum(amount for _, amount in tuition_items)
    
    primary_color = university_config['primary_color']
    uni_name = university_config['name']
    system_name = university_config['system_name']
    logo_text = university_config['logo_text']
    portal_name = university_config.get('portal_name', 'Student Accounts')
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{system_name} - Tuition Receipt</title>
    <style>
        body {{
            font-family: "Arial", sans-serif;
            background-color: #e5e5e5;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
        }}
        
        .receipt-container {{
            width: 850px;
            background: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            padding: 40px;
        }}
        
        .header {{
            border-bottom: 3px solid {primary_color};
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .logo {{
            font-size: 28px;
            font-weight: bold;
            color: {primary_color};
            margin-bottom: 5px;
        }}
        
        .uni-name {{
            font-size: 16px;
            color: #666;
        }}
        
        .receipt-title {{
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            color: {primary_color};
            margin: 20px 0;
        }}
        
        .student-info {{
            background: #f9f9f9;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid {primary_color};
        }}
        
        .info-row {{
            display: flex;
            margin: 8px 0;
        }}
        
        .info-label {{
            width: 180px;
            color: #666;
            font-weight: 500;
        }}
        
        .info-value {{
            color: #000;
            font-weight: 600;
        }}
        
        .charges-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
        }}
        
        .charges-table th {{
            background: {primary_color};
            color: white;
            padding: 12px;
            text-align: left;
        }}
        
        .charges-table td {{
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        
        .total-row {{
            font-weight: bold;
            font-size: 18px;
            background: #f0f0f0;
        }}
        
        .paid-stamp {{
            text-align: center;
            margin: 30px 0;
        }}
        
        .stamp {{
            display: inline-block;
            border: 3px solid #28a745;
            color: #28a745;
            font-size: 32px;
            font-weight: bold;
            padding: 15px 40px;
            transform: rotate(-5deg);
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 11px;
            color: #888;
            text-align: center;
        }}
    </style>
</head>
<body>

<div class="receipt-container">
    <div class="header">
        <div class="logo">{logo_text}</div>
        <div class="uni-name">{uni_name}</div>
        <div class="uni-name">{portal_name}</div>
    </div>
    
    <div class="receipt-title">OFFICIAL TUITION RECEIPT</div>
    
    <div class="student-info">
        <div class="info-row">
            <div class="info-label">Student Name:</div>
            <div class="info-value">{name}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Student ID:</div>
            <div class="info-value">{student_id}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Academic Program:</div>
            <div class="info-value">{major}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Academic Year:</div>
            <div class="info-value">{academic_year}</div>
        </div>
        <div class="info-row">
            <div class="info-label">Term:</div>
            <div class="info-value">{term} ({term_dates})</div>
        </div>
        <div class="info-row">
            <div class="info-label">Receipt Date:</div>
            <div class="info-value">{date}</div>
        </div>
    </div>
    
    <table class="charges-table">
        <thead>
            <tr>
                <th>Description</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {"".join(f'<tr><td>{item_name}</td><td style="text-align: right;">${amount:,.2f}</td></tr>' for item_name, amount in tuition_items)}
            <tr class="total-row">
                <td>TOTAL PAID</td>
                <td style="text-align: right;">${total_amount:,.2f}</td>
            </tr>
        </tbody>
    </table>
    
    <div class="paid-stamp">
        <div class="stamp">PAID IN FULL</div>
    </div>
    
    <div class="footer">
        <p>This is an official receipt issued by {uni_name}</p>
        <p>Generated: {date} | Document ID: RCP-{random.randint(100000, 999999)}</p>
        <p>&copy; {datetime.now().year} {uni_name}. All rights reserved.</p>
    </div>
</div>

</body>
</html>
"""
    
    return html


def generate_enrollment_verification_html(first_name: str, last_name: str, university_key: str, university_config: dict) -> str:
    """Generate Enrollment Verification Letter HTML"""
    student_id = generate_university_id(university_key)
    name = f"{first_name} {last_name}"
    date = datetime.now().strftime('%B %d, %Y')
    major = get_random_major()
    term, _ = get_random_term()
    
    primary_color = university_config['primary_color']
    uni_name = university_config['name']
    logo_text = university_config['logo_text']
    
    enrollment_status = random.choice(['Full-time', 'Full-time'])  # Mostly full-time
    units = random.randint(12, 18)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Enrollment Verification</title>
    <style>
        body {{
            font-family: "Times New Roman", Times, serif;
            background-color: #e8e8e8;
            margin: 0;
            padding: 30px;
            display: flex;
            justify-content: center;
        }}
        
        .letter-container {{
            width: 800px;
            background: white;
            box-shadow: 0 3px 20px rgba(0,0,0,0.15);
            padding: 60px;
        }}
        
        .letterhead {{
            text-align: center;
            border-bottom: 2px solid {primary_color};
            padding-bottom: 25px;
            margin-bottom: 40px;
        }}
        
        .logo {{
            font-size: 32px;
            font-weight: bold;
            color: {primary_color};
            letter-spacing: 2px;
        }}
        
        .uni-name {{
            font-size: 18px;
            color: #333;
            margin: 10px 0;
        }}
        
        .office {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        
        .letter-date {{
            margin: 30px 0;
            color: #333;
        }}
        
        .letter-title {{
            font-size: 20px;
            font-weight: bold;
            color: {primary_color};
            text-align: center;
            margin: 30px 0;
        }}
        
        .letter-body {{
            line-height: 1.8;
            color: #333;
            font-size: 14px;
        }}
        
        .student-details {{
            background: #f9f9f9;
            border-left: 4px solid {primary_color};
            padding: 20px;
            margin: 25px 0;
        }}
        
        .detail-row {{
            display: flex;
            margin: 8px 0;
        }}
        
        .detail-label {{
            width: 200px;
            font-weight: 600;
        }}
        
        .signature-block {{
            margin-top: 60px;
        }}
        
        .signature-line {{
            border-top: 2px solid #000;
            width: 300px;
            margin-top: 50px;
        }}
        
        .signature-name {{
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .signature-title {{
            color: #666;
            font-size: 13px;
        }}
        
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 11px;
            color: #888;
            text-align: center;
        }}
    </style>
</head>
<body>

<div class="letter-container">
    <div class="letterhead">
        <div class="logo">{logo_text}</div>
        <div class="uni-name">{uni_name}</div>
        <div class="office">Office of the Registrar</div>
    </div>
    
    <div class="letter-date">{date}</div>
    
    <div class="letter-title">OFFICIAL ENROLLMENT VERIFICATION</div>
    
    <div class="letter-body">
        <p>To Whom It May Concern:</p>
        
        <p>This letter serves as official verification that the student named below is currently enrolled at {uni_name}.</p>
        
        <div class="student-details">
            <div class="detail-row">
                <div class="detail-label">Student Name:</div>
                <div>{name}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Student ID:</div>
                <div>{student_id}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Academic Program:</div>
                <div>{major}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Current Term:</div>
                <div>{term}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Enrollment Status:</div>
                <div>{enrollment_status} ({units} units)</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Expected Graduation:</div>
                <div>{random.choice(['May 2026', 'May 2027', 'December 2026'])}</div>
            </div>
        </div>
        
        <p>This document is issued in response to a request made by the above-named student. The information contained herein is true and accurate to the best of our knowledge as of the date of this letter.</p>
        
        <p>Should you require any additional information, please contact our office at registrar@{university_config['email_domain']} or call (555) {random.randint(100, 999)}-{random.randint(1000, 9999)}.</p>
    </div>
    
    <div class="signature-block">
        <div class="signature-line"></div>
        <div class="signature-name">{random.choice(['Dr. Sarah Johnson', 'Dr. Michael Chen', 'Dr. Jennifer Williams'])}</div>
        <div class="signature-title">University Registrar</div>
    </div>
    
    <div class="footer">
        <p>This is an official document issued by {uni_name}</p>
        <p>Document Verification Code: ENV-{random.randint(100000, 999999)}</p>
        <p>&copy; 2025 {uni_name}. All rights reserved.</p>
    </div>
</div>

</body>
</html>
"""
    
    return html


def generate_html(first_name: str, last_name: str, doc_type: DocumentType = None, university_key: str = None) -> str:
    """
    Generate HTML for student verification document
    
    Args:
        first_name: Student first name
        last_name: Student last name
        doc_type: Document type (if None, randomly selected)
        university_key: University key (if None, randomly selected)
        
    Returns:
        HTML string
    """
    # Randomly select document type if not provided
    if doc_type is None:
        doc_type = random.choice([
            DocumentType.CLASS_SCHEDULE,
            DocumentType.CLASS_SCHEDULE,  # Give class schedule higher weight
            DocumentType.TUITION_RECEIPT,
            DocumentType.ENROLLMENT_VERIFICATION,
        ])
    
    # Randomly select university if not provided
    if university_key is None:
        university_key, university_config = get_random_university()
    else:
        from utils.document_templates import UNIVERSITIES
        university_config = UNIVERSITIES[university_key]
    
    # Generate appropriate HTML based on document type
    if doc_type == DocumentType.CLASS_SCHEDULE:
        return generate_class_schedule_html(first_name, last_name, university_key, university_config)
    elif doc_type == DocumentType.TUITION_RECEIPT:
        return generate_tuition_receipt_html(first_name, last_name, university_key, university_config)
    elif doc_type == DocumentType.ENROLLMENT_VERIFICATION:
        return generate_enrollment_verification_html(first_name, last_name, university_key, university_config)
    else:
        # Default to class schedule
        return generate_class_schedule_html(first_name, last_name, university_key, university_config)


def generate_image(first_name: str, last_name: str, school_id: str = None, doc_type: DocumentType = None) -> bytes:
    """
    Generate student verification document PNG with realistic effects
    
    Args:
        first_name: Student first name
        last_name: Student last name
        school_id: (Deprecated, kept for compatibility)
        doc_type: Document type (if None, randomly selected)
        
    Returns:
        PNG image bytes
    """
    try:
        from playwright.sync_api import sync_playwright
        
        # Generate HTML
        html_content = generate_html(first_name, last_name, doc_type=doc_type)
        
        # Get randomized viewport and zoom
        viewport = randomize_viewport()
        zoom = get_random_zoom()
        
        # Use Playwright to screenshot
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            page = browser.new_page(viewport={'width': viewport[0], 'height': viewport[1]})
            
            # Set zoom level
            page.set_content(html_content, wait_until='load')
            page.evaluate(f'document.body.style.zoom = "{zoom}"')
            page.wait_for_timeout(500)  # Wait for styles to load
            
            screenshot_bytes = page.screenshot(type='png', full_page=True)
            browser.close()
        
        # Apply realistic screenshot effects
        screenshot_bytes = apply_all_effects(
            screenshot_bytes,
            noise_intensity=random.uniform(0.008, 0.015),
            blur_radius=random.uniform(0.25, 0.4),
            brightness_variation=True
        )
        
        return screenshot_bytes
        
    except ImportError:
        raise Exception("需要安装 playwright: pip install playwright && playwright install chromium")
    except Exception as e:
        raise Exception(f"生成图片失败: {str(e)}")


# Backward compatibility functions
def generate_psu_id():
    """Deprecated: Use generate_university_id() instead"""
    return generate_university_id('mit')


def generate_psu_email(first_name, last_name):
    """Deprecated: Use generate_university_email() instead"""
    return generate_university_email(first_name, last_name, 'mit')


if __name__ == '__main__':
    # Test code
    import io
    
    # Fix Windows console encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("测试多大学、多文档类型图片生成...")
    
    first_name = "John"
    last_name = "Smith"
    
    print(f"姓名: {first_name} {last_name}\n")
    
    # Test different document types
    doc_types = [
        DocumentType.CLASS_SCHEDULE,
        DocumentType.TUITION_RECEIPT,
        DocumentType.ENROLLMENT_VERIFICATION,
    ]
    
    for i, doc_type in enumerate(doc_types):
        try:
            print(f"生成 {doc_type.value}...")
            img_data = generate_image(first_name, last_name, doc_type=doc_type)
            
            filename = f'test_{doc_type.value}.png'
            with open(filename, 'wb') as f:
                f.write(img_data)
            
            print(f"✓ 图片生成成功! 大小: {len(img_data)} bytes")
            print(f"✓ 已保存为 {filename}\n")
            
        except Exception as e:
            print(f"✗ 错误: {e}\n")
