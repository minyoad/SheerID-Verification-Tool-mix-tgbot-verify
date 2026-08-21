"""Turnstile 验证诊断脚本（容器内运行）

用法：
    docker-compose exec tgbot python -u utils/diagnose_captcha.py "https://services.sheerid.com/verify/xxx/?verificationId=yyy"

输出：
    1. 部署代码版本检查（确认 captcha_solver.py 是否为新版）
    2. .env 加载情况（BOT_TOKEN / 打码 key，脱敏显示）
    3. requests 直连页面结果（状态码 / 是否含 turnstile 引用 / sitekey）
    4. Playwright 打开页面后的网络请求与 DOM 检查
"""
import re
import sys
from pathlib import Path

# 以脚本方式运行（python utils/diagnose_captcha.py）时，Python 只把脚本所在目录
# 加入 sys.path，需手动把项目根目录加进来，才能 import utils / config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

URL = sys.argv[1] if len(sys.argv) > 1 else ""

# 1. 代码版本检查
import inspect
import os

import utils.captcha_solver as cs

src = inspect.getsource(cs)
print("=" * 60)
print("[1] captcha_solver.py 版本检查")
print(f"    含网络监听提取(sitekey_from_requests): {'sitekey_from_requests' in src}")
print(f"    含 iframe 正则(_SITEKEY_IFRAME_RE): {'_SITEKEY_IFRAME_RE' in src}")
print(f"    含 shadow DOM 穿透(walk): {'shadowRoot' in src}")

# 2. .env 加载情况
print("=" * 60)
print("[2] 配置加载检查")
from config import load_env_file, BOT_TOKEN

load_env_file()
def mask(v: str) -> str:
    v = (v or "").strip()
    if not v or len(v) < 8:
        return "<空>"
    return f"{v[:4]}...{v[-4:]}"

print(f"    BOT_TOKEN: {mask(BOT_TOKEN)}")
print(f"    2CAPTCHA_API_KEY: {mask(os.getenv('2CAPTCHA_API_KEY', ''))}")
print(f"    CAPSOLVER_API_KEY: {mask(os.getenv('CAPSOLVER_API_KEY', ''))}")
print(f"    CAPTCHA_HEADLESS: {os.getenv('CAPTCHA_HEADLESS', '(未设置,默认true)')}")

if not URL:
    print("\n未传入验证页面 URL，跳过后续诊断。")
    sys.exit(0)

# 3. requests 直连
print("=" * 60)
print("[3] requests 直连页面")
try:
    import requests

    r = requests.get(URL, timeout=20, headers={
        "User-Agent": cs._UA,
        "Accept-Language": "en-US,en;q=0.9",
    })
    html = r.text
    print(f"    状态码: {r.status_code}")
    print(f"    最终URL: {r.url}")
    print(f"    页面大小: {len(html)} bytes")
    print(f"    含 turnstile 脚本引用: {'turnstile' in html.lower()}")
    sk = cs._extract_sitekey_from_html(html)
    print(f"    正则提取 sitekey: {mask(sk) if sk else '<未找到>'}")
    if "cloudflare" in r.url.lower():
        print("    ⚠️ 最终 URL 指向 cloudflare（可能被 challenge 拦截）")
except Exception as e:
    print(f"    requests 失败: {e}")

# 4. Playwright 网络请求 + DOM 检查
print("=" * 60)
print("[4] Playwright 打开页面诊断（20 秒窗口）")
try:
    from playwright.sync_api import sync_playwright

    cloudflare_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=cs._LAUNCH_ARGS)
        ctx = browser.new_context(user_agent=cs._UA, viewport={"width": 1280, "height": 800})
        ctx.add_init_script(cs._STEALTH_JS)
        page = ctx.new_page()

        def on_req(req):
            u = req.url
            if "cloudflare" in u or "turnstile" in u:
                cloudflare_urls.append(u)

        page.on("request", on_req)
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(20000)

        print(f"    抓到的 cloudflare/turnstile 请求: {len(cloudflare_urls)} 条")
        for u in cloudflare_urls[:15]:
            print(f"      - {u[:160]}")

        dom = page.evaluate(
            """() => ({
                hasTurnstile: !!window.turnstile,
                sitekeyDom: (() => {
                    const e = document.querySelector('[data-sitekey],[data-turnstile-sitekey]');
                    return e ? (e.getAttribute('data-sitekey') || e.getAttribute('data-turnstile-sitekey')) : '';
                })(),
                title: document.title,
                bodyStart: (document.body ? document.body.innerText.slice(0, 200) : ''),
            })"""
        )
        print(f"    window.turnstile 存在: {dom['hasTurnstile']}")
        print(f"    DOM sitekey: {mask(dom['sitekeyDom']) if dom['sitekeyDom'] else '<未找到>'}")
        print(f"    页面标题: {dom['title']}")
        print(f"    页面文本开头: {dom['bodyStart'][:120]!r}")
        browser.close()
except Exception as e:
    print(f"    Playwright 诊断失败: {e}")

print("=" * 60)
print("诊断结束")
