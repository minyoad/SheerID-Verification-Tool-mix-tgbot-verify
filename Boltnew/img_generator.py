"""PNG 教师证生成模块 - Multi-District & Multi-Document Type Support

Supports:
- Multiple document types: Employment Verification, Payroll Stub, Teacher Dashboard
- Multiple school districts: Springfield, Jefferson, Oakland, Seattle, Boston, Chicago
- Realistic screenshot effects: noise, blur, randomization
"""
import random
import sys
import os
from datetime import datetime, timedelta
from io import BytesIO

# Add parent directory to path for utils imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.document_templates import (
    DocumentType,
    SCHOOL_DISTRICTS,
    get_random_district,
    generate_district_id,
    generate_district_email,
)
from utils.image_effects import (
    apply_all_effects,
    randomize_viewport,
    get_random_zoom,
)


def generate_employment_verification_html(first_name: str, last_name: str, district_key: str, district_config: dict) -> str:
    """Generate Employment Verification document"""
    employee_id = generate_district_id(district_key)
    name = f"{first_name} {last_name}"
    date = datetime.now().strftime('%m/%d/%Y %I:%M %p')
    
    primary_color = district_config['primary_color']
    district_name = district_config['name']
    system_name = district_config['system_name']
    logo_text = district_config['logo_text']
    
    position_titles = [
        'Faculty - Science Department (FTE 1.0)',
        'Faculty - Mathematics Department (FTE 1.0)',
        'Faculty - English Department (FTE 1.0)',
        'Faculty - Social Studies (FTE 1.0)',
        'Elementary Teacher (FTE 1.0)',
        'Special Education Teacher (FTE 1.0)',
    ]
    position = random.choice(position_titles)
    
    schools = [
        'North High School',
        'Central High School',
        'East Elementary School',
        'West Middle School',
        'Lincoln Elementary School',
    ]
    location = f"{district_config['short_name']} {random.choice(schools)}"
    
    hire_year = random.randint(2015, 2023)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{system_name} - Employment Verification</title>
    <style>
        :root {{
            --primary-blue: {primary_color};
            --border-gray: #dee2e6;
            --bg-gray: #f8f9fa;
        }}

        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #e9ecef;
            margin: 0;
            padding: 20px;
            font-size: 14px;
            color: #333;
        }}

        .browser-mockup {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-radius: 4px;
            overflow: hidden;
        }}

        .system-header {{
            background: var(--primary-blue);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .district-name {{
            font-size: 18px;
            font-weight: bold;
            display: flex;
            align-items: center;
        }}

        .district-logo-placeholder {{
            width: 30px; height: 30px; background: white; border-radius: 50%; margin-right: 10px;
            display: flex; align-items: center; justify-content: center; color: var(--primary-blue); font-weight: 900;
        }}

        .user-nav {{ font-size: 13px; }}
        .user-nav span {{ margin-left: 15px; cursor: pointer; opacity: 0.8; }}

        .breadcrumb {{
            background: #f0f2f5;
            padding: 10px 20px;
            border-bottom: 1px solid var(--border-gray);
            color: #666;
            font-size: 12px;
        }}

        .main-content {{
            padding: 30px;
        }}

        .page-title {{
            font-size: 22px;
            margin-bottom: 25px;
            color: #2c3e50;
            border-bottom: 3px solid var(--primary-blue);
            padding-bottom: 10px;
            display: inline-block;
        }}

        .tabs {{
            display: flex;
            border-bottom: 1px solid var(--border-gray);
            margin-bottom: 20px;
        }}
        .tab {{
            padding: 10px 20px;
            border: 1px solid transparent;
            cursor: pointer;
            color: var(--primary-blue);
        }}
        .tab.active {{
            border: 1px solid var(--border-gray);
            border-bottom-color: white;
            background: white;
            color: #333;
            font-weight: bold;
            margin-bottom: -1px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}

        .data-panel {{
            border: 1px solid var(--border-gray);
            border-radius: 4px;
            margin-bottom: 25px;
        }}
        .panel-header {{
            background: var(--bg-gray);
            padding: 10px 15px;
            font-weight: bold;
            border-bottom: 1px solid var(--border-gray);
        }}
        .panel-body {{ padding: 20px; }}

        .info-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .info-table th, .info-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .info-table th {{
            width: 30%;
            color: #666;
            font-weight: normal;
            background-color: #fafafa;
        }}
        .info-table td {{
            font-weight: 600;
            color: #000;
        }}

        .status-active {{
            background-color: #d4edda;
            color: #155724;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 12px;
            display: inline-block;
        }}

        .system-footer {{
            padding: 15px 30px;
            background: #f8f9fa;
            border-top: 1px solid var(--border-gray);
            font-size: 11px;
            color: #888;
            display: flex;
            justify-content: space-between;
        }}
    </style>
</head>
<body>

<div class="browser-mockup">
    <div class="system-header">
        <div class="district-name">
            <div class="district-logo-placeholder">{logo_text}</div>
            {district_name} - {system_name}
        </div>
        <div class="user-nav">
            Welcome, <span>{name}</span> | My Account | Sign Out
        </div>
    </div>

    <div class="breadcrumb">
        Home > Employee Self Service > Employment > Current Assignment Information
    </div>

    <div class="main-content">
        <h1 class="page-title">Current Job Summary & Verification</h1>

        <div class="tabs">
            <div class="tab active">Assignment Details</div>
            <div class="tab">Compensation History</div>
            <div class="tab">Certifications</div>
        </div>

        <div class="data-panel">
            <div class="panel-header">Employee Information</div>
            <div class="panel-body">
                <table class="info-table">
                    <tr>
                        <th>Employee Name:</th>
                        <td style="font-size: 16px;">{name}</td>
                    </tr>
                    <tr>
                        <th>Employee ID:</th>
                        <td>{employee_id}</td>
                    </tr>
                    <tr>
                        <th>Current Status:</th>
                        <td><span class="status-active">Active / Active Payroll</span></td>
                    </tr>
                </table>
            </div>
        </div>

        <div class="data-panel">
            <div class="panel-header">Primary Assignment Details (Academic Year 2025-2026)</div>
            <div class="panel-body">
                <table class="info-table">
                    <tr>
                        <th>Primary Location:</th>
                        <td>{location}</td>
                    </tr>
                    <tr>
                        <th>Position / Job Title:</th>
                        <td>{position}</td>
                    </tr>
                    <tr>
                        <th>Employee Type:</th>
                        <td>Certified Faculty / Staff</td>
                    </tr>
                    <tr>
                        <th>Hire Date:</th>
                        <td>August 15, {hire_year}</td>
                    </tr>
                    <tr>
                        <th>Assignment Dates:</th>
                        <td>August 20, 2025 - June 10, 2026</td>
                    </tr>
                </table>
            </div>
        </div>

    </div>

    <div class="system-footer">
        <div>System Report Generated: <span>{date}</span></div>
        <div>Environment: PROD | Database: HR_SYS | Version: 12.4.0.88</div>
    </div>
</div>

</body>
</html>
"""
    
    return html


def generate_payroll_stub_html(first_name: str, last_name: str, district_key: str, district_config: dict) -> str:
    """Generate Payroll Stub document"""
    employee_id = generate_district_id(district_key)
    name = f"{first_name} {last_name}"
    
    # Generate stub for recent pay period
    pay_date = datetime.now() - timedelta(days=random.randint(1, 14))
    pay_period_start = pay_date - timedelta(days=14)
    pay_period_end = pay_date - timedelta(days=1)
    
    primary_color = district_config['primary_color']
    district_name = district_config['name']
    
    # Generate salary numbers
    gross_pay = random.uniform(3500, 5500)
    federal_tax = gross_pay * random.uniform(0.15, 0.22)
    state_tax = gross_pay * random.uniform(0.05, 0.08)
    social_security = gross_pay * 0.062
    medicare = gross_pay * 0.0145
    retirement = gross_pay * random.uniform(0.06, 0.08)
    
    total_deductions = federal_tax + state_tax + social_security + medicare + retirement
    net_pay = gross_pay - total_deductions
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Payroll Statement</title>
    <style>
        body {{
            font-family: 'Courier New', Courier, monospace;
            background-color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }}
        
        .payslip-container {{
            width: 850px;
            background: white;
            margin: 0 auto;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        .header {{
            border-bottom: 3px double {primary_color};
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        .district-title {{
            font-size: 20px;
            font-weight: bold;
            color: {primary_color};
            margin-bottom: 5px;
        }}
        
        .slip-title {{
            font-size: 16px;
            text-align: center;
            margin: 15px 0;
            font-weight: bold;
        }}
        
        .info-section {{
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
        }}
        
        .info-block {{
            flex: 1;
        }}
        
        .info-row {{
            display: flex;
            margin: 5px 0;
        }}
        
        .info-label {{
            width: 150px;
            font-weight: bold;  
        }}
        
        .pay-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        .pay-table th {{
            background: {primary_color};
            color: white;
            padding: 8px;
            text-align: left;
            font-size: 13px;
        }}
        
        .pay-table td {{
            padding: 8px;
            border-bottom: 1px dashed #ccc;
        }}
        
        .total-row {{
            font-weight: bold;
            background: #f5f5f5;
        }}
        
        .net-pay {{
            font-size: 18px;
            font-weight: bold;
            text-align: right;
            padding: 15px;
            background: #e8f5e9;
            border: 2px solid #4caf50;
            margin: 20px 0;
        }}
        
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ccc;
            font-size: 10px;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>

<div class="payslip-container">
    <div class="header">
        <div class="district-title">{district_name}</div>
        <div>Payroll Department</div>
    </div>
    
    <div class="slip-title">EARNINGS STATEMENT</div>
    
    <div class="info-section">
        <div class="info-block">
            <div class="info-row">
                <div class="info-label">Employee Name:</div>
                <div>{name}</div>
            </div>
            <div class="info-row">
                <div class="info-label">Employee ID:</div>
                <div>{employee_id}</div>
            </div>
            <div class="info-row">
                <div class="info-label">Pay Period:</div>
                <div>{pay_period_start.strftime('%m/%d/%Y')} - {pay_period_end.strftime('%m/%d/%Y')}</div>
            </div>
        </div>
        <div class="info-block">
            <div class="info-row">
                <div class="info-label">Pay Date:</div>
                <div>{pay_date.strftime('%m/%d/%Y')}</div>
            </div>
            <div class="info-row">
                <div class="info-label">Status:</div>
                <div>Full-time Certified</div>
            </div>
        </div>
    </div>
    
    <table class="pay-table">
        <thead>
            <tr>
                <th>Earnings</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Regular Salary</td>
                <td style="text-align: right;">${gross_pay:,.2f}</td>
            </tr>
            <tr class="total-row">
                <td>Gross Pay</td>
                <td style="text-align: right;">${gross_pay:,.2f}</td>
            </tr>
        </tbody>
    </table>
    
    <table class="pay-table">
        <thead>
            <tr>
                <th>Deductions</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Federal Income Tax</td>
                <td style="text-align: right;">${federal_tax:,.2f}</td>
            </tr>
            <tr>
                <td>State Income Tax</td>
                <td style="text-align: right;">${state_tax:,.2f}</td>
            </tr>
            <tr>
                <td>Social Security</td>
                <td style="text-align: right;">${social_security:,.2f}</td>
            </tr>
            <tr>
                <td>Medicare</td>
                <td style="text-align: right;">${medicare:,.2f}</td>
            </tr>
            <tr>
                <td>Retirement Contribution</td>
                <td style="text-align: right;">${retirement:,.2f}</td>
            </tr>
            <tr class="total-row">
                <td>Total Deductions</td>
                <td style="text-align: right;">${total_deductions:,.2f}</td>
            </tr>
        </tbody>
    </table>
    
    <div class="net-pay">
        NET PAY: ${net_pay:,.2f}
    </div>
    
    <div class="footer">
        <p>*** This is a computer-generated statement and does not require a signature ***</p>
        <p>{district_name} - Confidential Payroll Document</p>
        <p>Document ID: PAY-{random.randint(100000, 999999)}</p>
    </div>
</div>

</body>
</html>
"""
    
    return html


def generate_teacher_dashboard_html(first_name: str, last_name: str, district_key: str, district_config: dict) -> str:
    """Generate Teacher Dashboard view (simplified employment verification)"""
    # This is basically the same as employment verification
    return generate_employment_verification_html(first_name, last_name, district_key, district_config)


def generate_html(first_name: str, last_name: str, doc_type: DocumentType = None, district_key: str = None) -> str:
    """
    Generate HTML for teacher verification document
    
    Args:
        first_name: Teacher first name
        last_name: Teacher last name
        doc_type: Document type (if None, randomly selected)
        district_key: School district key (if None, randomly selected)
        
    Returns:
        HTML string
    """
    # Randomly select document type if not provided
    if doc_type is None:
        doc_type = random.choice([
            DocumentType.EMPLOYMENT_VERIFICATION,
            DocumentType.EMPLOYMENT_VERIFICATION,  # Give employment verification higher weight
            DocumentType.TEACHER_DASHBOARD,
            DocumentType.PAYROLL_STUB,
        ])
    
    # Randomly select district if not provided
    if district_key is None:
        district_key, district_config = get_random_district()
    else:
        district_config = SCHOOL_DISTRICTS[district_key]
    
    # Generate appropriate HTML based on document type
    if doc_type in [DocumentType.EMPLOYMENT_VERIFICATION, DocumentType.TEACHER_DASHBOARD]:
        return generate_employment_verification_html(first_name, last_name, district_key, district_config)
    elif doc_type == DocumentType.PAYROLL_STUB:
        return generate_payroll_stub_html(first_name, last_name, district_key, district_config)
    else:
        # Default to employment verification
        return generate_employment_verification_html(first_name, last_name, district_key, district_config)


def generate_teacher_png(first_name: str, last_name: str, doc_type: DocumentType = None) -> bytes:
    """
    Generate teacher verification document PNG with realistic effects
    
    Args:
        first_name: Teacher first name
        last_name: Teacher last name
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
            
            page.set_content(html_content, wait_until='load')
            page.evaluate(f'document.body.style.zoom = "{zoom}"')
            page.wait_for_timeout(500)
            
            # Try to screenshot the .browser-mockup element, fallback to full page
            try:
                card = page.locator('.browser-mockup, .payslip-container')
                png_bytes = card.screenshot(type='png')
            except:
                png_bytes = page.screenshot(type='png', full_page=True)
            
            browser.close()
        
        # Apply realistic screenshot effects
        png_bytes = apply_all_effects(
            png_bytes,
            noise_intensity=random.uniform(0.008, 0.015),
            blur_radius=random.uniform(0.25, 0.4),
            brightness_variation=True
        )
        
        return png_bytes
        
    except ImportError:
        raise RuntimeError("需要安装 playwright，请执行 `pip install playwright` 然后 `playwright install chromium`")
    except Exception as e:
        raise Exception(f"生成图片失败: {str(e)}")


# Backward compatibility
def generate_teacher_image(first_name: str, last_name: str) -> bytes:
    """Backward compatibility: Generate teacher verification image"""
    return generate_teacher_png(first_name, last_name)


def generate_teacher_pdf(first_name: str, last_name: str) -> bytes:
    """Deprecated: PDF generation removed, returns PNG instead"""
    return generate_teacher_png(first_name, last_name)


# ===========================================================================
# BOLTNEW BACKWARD COMPATIBILITY LAYER
# ===========================================================================

def generate_psu_email(first_name, last_name):
    """Backward compatibility: Generate email address for teacher"""
    district_key, _ = get_random_district()
    return generate_district_email(first_name, last_name, district_key)


def generate_images(first_name, last_name, school_id=None):
    """
    Backward compatibility: Generate teacher images in old format
    
    Returns list of dicts with 'file_name' and 'data' keys for Boltnew compatibility
    """
    png_data = generate_teacher_png(first_name, last_name)
    return [
        {
            'file_name': 'teacher_verification.png',
            'data': png_data
        }
    ]


if __name__ == '__main__':
    # Test code
    import io
    
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("测试多学区、多文档类型教师证生成...")
    
    first_name = "Sarah"
    last_name = "Johnson"
    
    print(f"姓名: {first_name} {last_name}\n")
    
    doc_types = [
        DocumentType.EMPLOYMENT_VERIFICATION,
        DocumentType.PAYROLL_STUB,
    ]
    
    for doc_type in doc_types:
        try:
            print(f"生成 {doc_type.value}...")
            img_data = generate_teacher_png(first_name, last_name, doc_type=doc_type)
            
            filename = f'test_teacher_{doc_type.value}.png'
            with open(filename, 'wb') as f:
                f.write(img_data)
            
            print(f"✓ 图片生成成功! 大小: {len(img_data)} bytes")
            print(f"✓ 已保存为 {filename}\n")
            
        except Exception as e:
            print(f"✗ 错误: {e}\n")
