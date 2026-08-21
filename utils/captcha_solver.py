"""Cloudflare Turnstile 验证码 token 获取工具（增强版）

SheerID 在学生/教师信息提交步骤启用了 Cloudflare Turnstile 人机验证，
请求体需要携带 captchaToken 字段（缺失时返回 invalidCaptchaToken 错误）。

获取策略（按优先级自动选择）：
1. Playwright 反检测浏览器自动完成 Turnstile 验证
   - 完整浏览器指纹（webdriver 覆盖、plugins 填充、语言/时区/平台一致性、UA 匹配）
   - 等待 turnstile 脚本加载后主动触发 window.turnstile.execute()
   - 多策略提取 token（隐藏字段 / turnstile API / 按 widget id）
2. 第三方打码服务兜底（配置 CAPSOLVER_API_KEY 或 2CAPTCHA_API_KEY 时自动启用）
   - 先从页面 HTML 提取 sitekey，再调用打码 API 获取 token

配置（环境变量）：
    CAPTCHA_HEADLESS     是否无头模式，默认 true；容器内无 DISPLAY 时自动回退无头
    CAPTCHA_FORCE_HEADED 强制有头模式（跳过 DISPLAY 检测，需自行保证 xvfb 可用）
    CAPSOLVER_API_KEY    capsolver 打码服务 API Key（兜底）
    2CAPTCHA_API_KEY     2captcha 打码服务 API Key（兜底）

用法：
    from utils.captcha_solver import get_turnstile_token
    token = get_turnstile_token("https://services.sheerid.com/verify/xxx/?verificationId=yyy")
"""
import logging
import os
import re
import time
from typing import Tuple

from dotenv import load_dotenv

# 确保 .env 被加载（即使从子模块/独立脚本入口运行，也能读到打码服务 key）
load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60

# 与注入指纹一致的 Windows Chrome UA
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# 反检测浏览器启动参数（Docker 容器兼容 + 降低自动化指纹）
_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-default-apps",
    "--mute-audio",
    "--lang=en-US",
]

# 注入页面，抹除常见自动化指纹
_STEALTH_JS = """
// 隐藏 webdriver 标记
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 语言列表与 UA 一致
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

// plugins 非空（headless 默认为空数组，易被识别）
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// chrome runtime 对象（部分站点检测）
window.chrome = window.chrome || { runtime: {} };

// 权限查询行为对齐真实浏览器
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);

// WebGL 渲染器供应商（避免暴露 SwiftShader/ANGLE）
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter(parameter);
};
"""

_SITEKEY_ATTR_RE = re.compile(
    r'(?:data-sitekey|data-turnstile-sitekey)="([A-Za-z0-9_-]{20,})"'
)
_SITEKEY_RENDER_RE = re.compile(
    r'turnstile[^"\']*render=(?:"|&quot;)?([A-Za-z0-9_-]{20,})'
)


def get_turnstile_token(verification_url: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """入口：按优先级尝试多种策略获取 Turnstile token

    Args:
        verification_url: SheerID 验证页面 URL（含 verificationId）
        timeout: 最大等待秒数（Playwright 阶段）

    Returns:
        str: Turnstile token，全部失败返回空字符串
    """
    sitekey = _fetch_sitekey_via_requests(verification_url)
    action, cdata = _extract_turnstile_meta_from_html(_last_fetched_html)

    token, dom_sitekey, dom_action, dom_cdata = _solve_with_playwright(
        verification_url, timeout
    )
    if token:
        logger.info("✓ Turnstile token 获取成功（Playwright 自动完成）")
        return token

    if dom_sitekey and not sitekey:
        sitekey = dom_sitekey
    action = action or dom_action
    cdata = cdata or dom_cdata

    token = _solve_with_third_party(verification_url, sitekey, action, cdata)
    if token:
        logger.info("✓ Turnstile token 获取成功（第三方打码服务）")
    return token


# ---------------------------------------------------------------------------
# 策略 1：Playwright 反检测浏览器
# ---------------------------------------------------------------------------
def _solve_with_playwright(verification_url: str, timeout: int) -> Tuple[str, str, str, str]:
    """通过 Playwright 打开验证页面自动完成验证；返回 (token, sitekey, action, cdata)"""
    token = ""
    sitekey = ""
    action = ""
    cdata = ""
    browser = None
    headless = os.getenv("CAPTCHA_HEADLESS", "true").strip().lower() != "false"
    force_headed = os.getenv("CAPTCHA_FORCE_HEADED", "").strip().lower() == "true"

    # 有头模式但容器内无 X server（未配 xvfb）时自动回退无头
    if not headless and not force_headed and not os.environ.get("DISPLAY"):
        logger.warning(
            "CAPTCHA_HEADLESS=false 但未检测到 DISPLAY（容器内缺少 xvfb），"
            "自动回退 headless 模式；如需有头模式请用 xvfb-run 启动容器进程"
        )
        headless = True

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=headless, args=_LAUNCH_ARGS)
            except Exception as e:
                if headless:
                    raise
                # 有头模式启动失败（如无 X server），回退无头重试
                logger.warning(f"有头模式启动失败（{e}），自动回退 headless 重试")
                headless = True
                browser = p.chromium.launch(headless=headless, args=_LAUNCH_ARGS)

            context = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="light",
                device_scale_factor=1,
            )
            context.add_init_script(_STEALTH_JS)
            page = context.new_page()

            logger.info(f"打开验证页面: {verification_url}")
            page.goto(verification_url, wait_until="domcontentloaded", timeout=30000)

            # 等待 turnstile 脚本加载完成
            _wait_turnstile_loaded(page)

            # 提取 sitekey（供第三方兜底使用），并用完整 HTML 兜底
            sitekey = _extract_sitekey(page)
            try:
                html = page.content()
                if not sitekey:
                    sitekey = _extract_sitekey_from_html(html)
                if not sitekey:
                    # SPA 渲染后 sitekey 可能在 widget 配置 JSON 中
                    m = re.search(r'["\']sitekey["\']\s*:\s*["\']([A-Za-z0-9_-]{20,})["\']', html)
                    if m:
                        sitekey = m.group(1)
                action, cdata = _extract_turnstile_meta_from_html(html)
            except Exception:
                pass
            if sitekey:
                logger.info(f"已提取 Turnstile sitekey: {sitekey[:8]}...（action={action or '-'}）")

            # 主动触发 turnstile 执行（自动执行模式未生效时）
            _trigger_turnstile(page)

            # 轮询提取 token
            start = time.time()
            while time.time() - start < timeout:
                token = _poll_token(page)
                if token:
                    break
                time.sleep(2)

            if not token:
                logger.warning(
                    "Playwright 在限定时间内未获取到 Turnstile token"
                    "（headless 模式可能被 Cloudflare 判定为机器人；"
                    "可尝试 CAPTCHA_HEADLESS=false + xvfb，或配置打码服务兜底）"
                )
    except Exception as e:
        logger.error(f"Playwright 获取 Turnstile token 异常: {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return token, sitekey, action, cdata


def _wait_turnstile_loaded(page, wait_secs: int = 10) -> bool:
    """等待 window.turnstile 可用"""
    start = time.time()
    while time.time() - start < wait_secs:
        try:
            if page.evaluate("() => !!window.turnstile"):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _trigger_turnstile(page):
    """主动触发 turnstile 执行（自动执行模式未生效时）"""
    try:
        page.evaluate(
            """() => {
                if (!window.turnstile) return;
                // 方式1：execute() 不带参数（执行所有/默认 widget）
                try { window.turnstile.execute(); } catch (e) {}
                // 方式2：对已渲染的每个 widget 逐个执行
                try {
                    const widgets = window.turnstile._c || [];
                    for (let i = 0; i < widgets.length; i++) {
                        if (!widgets[i]) continue;
                        try { window.turnstile.execute(i); } catch (e) {}
                    }
                } catch (e) {}
            }"""
        )
    except Exception:
        pass


def _poll_token(page) -> str:
    """多策略提取 token：隐藏字段 / turnstile API / 按 widget id"""
    try:
        return (
            page.evaluate(
                """() => {
                    // 方式1：读取 cf-turnstile-response 隐藏字段
                    const inputs = document.querySelectorAll(
                        'input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"]'
                    );
                    for (const el of inputs) {
                        if (el.value) return el.value;
                    }
                    if (!window.turnstile) return '';
                    // 方式2：getResponse() 不带参数
                    try {
                        const r = window.turnstile.getResponse();
                        if (r) return r;
                    } catch (e) {}
                    // 方式3：按 widget id 逐个获取
                    try {
                        const widgets = window.turnstile._c || [];
                        for (let i = 0; i < widgets.length; i++) {
                            if (!widgets[i]) continue;
                            try {
                                const r = window.turnstile.getResponse(i);
                                if (r) return r;
                            } catch (e) {}
                        }
                    } catch (e) {}
                    return '';
                }"""
            )
            or ""
        )
    except Exception:
        return ""


def _extract_sitekey(page) -> str:
    """从 DOM 中提取 Turnstile sitekey（供第三方兜底使用）"""
    try:
        return (
            page.evaluate(
                """() => {
                    const el = document.querySelector(
                        '[data-sitekey], [data-turnstile-sitekey]'
                    );
                    if (el) {
                        return el.getAttribute('data-sitekey') ||
                               el.getAttribute('data-turnstile-sitekey');
                    }
                    const scripts = Array.from(
                        document.querySelectorAll('script[src*="turnstile"]')
                    );
                    for (const s of scripts) {
                        const m = s.src.match(/render=([A-Za-z0-9_-]{20,})/);
                        if (m) return m[1];
                    }
                    return '';
                }"""
            )
            or ""
        )
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# sitekey 提取（requests 直连，供第三方兜底）
# ---------------------------------------------------------------------------
# 最近一次 requests 抓取的页面 HTML，供后续提取 data-action / data-cdata
_last_fetched_html = ""


def _fetch_sitekey_via_requests(page_url: str) -> str:
    """直接用 requests 抓取页面 HTML，正则提取 Turnstile sitekey"""
    global _last_fetched_html
    try:
        import requests

        r = requests.get(
            page_url,
            timeout=15,
            headers={
                "User-Agent": _UA,
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        _last_fetched_html = r.text
        return _extract_sitekey_from_html(r.text)
    except Exception as e:
        logger.debug(f"requests 提取 sitekey 失败: {e}")
        _last_fetched_html = ""
        return ""


def _extract_sitekey_from_html(html: str) -> str:
    if not html:
        return ""
    m = _SITEKEY_ATTR_RE.search(html)
    if m:
        return m.group(1)
    m = _SITEKEY_RENDER_RE.search(html)
    if m:
        return m.group(1)
    return ""


def _extract_turnstile_meta_from_html(html: str) -> Tuple[str, str]:
    """从页面 HTML 提取 data-action 与 data-cdata（2captcha Turnstile 可选参数）"""
    if not html:
        return "", ""
    action = ""
    cdata = ""
    m = re.search(r'data-action="([^"]+)"', html)
    if m:
        action = m.group(1)
    m = re.search(r'data-cdata="([^"]+)"', html)
    if m:
        cdata = m.group(1)
    return action, cdata


# ---------------------------------------------------------------------------
# 策略 2：第三方打码服务兜底
# ---------------------------------------------------------------------------
def _solve_with_third_party(
    page_url: str, sitekey: str, action: str = "", cdata: str = ""
) -> str:
    """调用第三方打码服务获取 token；未配置 key 或缺少 sitekey 时返回空串"""
    if not sitekey:
        logger.warning("无法提取 Turnstile sitekey，第三方打码服务不可用")
        return ""

    capsolver_key = os.getenv("CAPSOLVER_API_KEY", "").strip()
    twocaptcha_key = os.getenv("2CAPTCHA_API_KEY", "").strip()

    if capsolver_key:
        return _solve_with_capsolver(page_url, sitekey, capsolver_key)
    if twocaptcha_key:
        return _solve_with_2captcha(page_url, sitekey, twocaptcha_key, action, cdata)

    logger.warning(
        "未检测到第三方打码服务 key（2CAPTCHA_API_KEY / CAPSOLVER_API_KEY 均为空）。"
        "请确认：① 已创建项目根目录 .env 并填入 key；"
        "② Docker 部署时 docker-compose 已转发该变量到容器"
        "（注意 2CAPTCHA_API_KEY 以数字开头，Compose 的 .env 解析不支持，"
        "需用 export 或 systemd Environment= 传入）；"
        "③ 重启 bot 进程使配置生效"
    )
    return ""


def _solve_with_capsolver(page_url: str, sitekey: str, api_key: str) -> str:
    """capsolver: AntiTurnstileTaskProxyLess"""
    try:
        import requests
    except Exception as e:
        logger.error(f"requests 不可用，无法调用 capsolver: {e}")
        return ""

    try:
        resp = requests.post(
            "https://api.capsolver.com/createTask",
            json={
                "clientKey": api_key,
                "task": {
                    "type": "AntiTurnstileTaskProxyLess",
                    "websiteURL": page_url,
                    "websiteKey": sitekey,
                },
            },
            timeout=20,
        )
        data = resp.json()
        task_id = data.get("taskId")
        if not task_id:
            logger.warning(f"capsolver createTask 失败: {data.get('errorDescription') or data}")
            return ""

        start = time.time()
        while time.time() - start < 120:
            time.sleep(5)
            r = requests.post(
                "https://api.capsolver.com/getTaskResult",
                json={"clientKey": api_key, "taskId": task_id},
                timeout=20,
            )
            d = r.json()
            if d.get("status") == "ready":
                token = d.get("solution", {}).get("token", "")
                if token:
                    return token
            if d.get("status") == "failed":
                logger.warning(f"capsolver 任务失败: {d}")
                return ""
    except Exception as e:
        logger.error(f"capsolver 调用失败: {e}")
    return ""


def _solve_with_2captcha(
    page_url: str, sitekey: str, api_key: str, action: str = "", cdata: str = ""
) -> str:
    """2captcha: method=turnstile（页面 widget 带 data-action/data-cdata 时需一并传入）"""
    try:
        import requests
    except Exception as e:
        logger.error(f"requests 不可用，无法调用 2captcha: {e}")
        return ""

    try:
        params = {
            "key": api_key,
            "method": "turnstile",
            "sitekey": sitekey,
            "pageurl": page_url,
            "json": 1,
        }
        if action:
            params["action"] = action
        if cdata:
            params["data"] = cdata
        r = requests.get(
            "https://2captcha.com/in.php",
            params=params,
            timeout=20,
        )
        data = r.json()
        if data.get("status") != 1:
            logger.warning(f"2captcha in.php 失败: {data}")
            return ""
        captcha_id = data.get("request", "")

        start = time.time()
        while time.time() - start < 120:
            time.sleep(5)
            r = requests.get(
                "https://2captcha.com/res.php",
                params={
                    "key": api_key,
                    "action": "get",
                    "id": captcha_id,
                    "json": 1,
                },
                timeout=20,
            )
            d = r.json()
            if d.get("status") == 1:
                return d.get("request", "")
            if d.get("request") not in ("CAPCHA_NOT_READY", "NOT_READY"):
                logger.warning(f"2captcha 任务失败: {d}")
                return ""
    except Exception as e:
        logger.error(f"2captcha 调用失败: {e}")
    return ""
