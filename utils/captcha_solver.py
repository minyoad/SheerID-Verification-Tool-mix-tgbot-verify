"""Cloudflare Turnstile 验证码 token 获取工具

SheerID 在学生/教师信息提交步骤启用了 Cloudflare Turnstile 人机验证，
请求体需要携带 captchaToken 字段（缺失时返回 invalidCaptchaToken 错误）。

本工具通过 Playwright 打开 SheerID 验证页面，等待 Turnstile widget
自动完成验证后提取 token。

用法：
    from utils.captcha_solver import get_turnstile_token
    token = get_turnstile_token("https://services.sheerid.com/verify/xxx/?verificationId=yyy")
"""
import logging
import time

logger = logging.getLogger(__name__)


def get_turnstile_token(verification_url: str, timeout: int = 60) -> str:
    """通过 Playwright 打开验证页面，自动完成 Turnstile 验证并获取 token

    Args:
        verification_url: SheerID 验证页面 URL（含 verificationId）
        timeout: 最大等待秒数

    Returns:
        str: Turnstile token，获取失败返回空字符串
    """
    from playwright.sync_api import sync_playwright

    token = ""
    browser = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            page = context.new_page()

            logger.info(f"打开验证页面: {verification_url}")
            page.goto(verification_url, wait_until="domcontentloaded", timeout=30000)

            # 轮询等待 Turnstile 完成，提取 token
            start = time.time()
            while time.time() - start < timeout:
                token = page.evaluate(
                    """() => {
                        // 方式1: 读取 cf-turnstile-response 隐藏字段
                        const inputs = document.querySelectorAll(
                            'input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"]'
                        );
                        for (const el of inputs) {
                            if (el.value) return el.value;
                        }
                        // 方式2: 通过 turnstile API 获取
                        if (window.turnstile) {
                            try {
                                const resp = window.turnstile.getResponse();
                                if (resp) return resp;
                            } catch (e) {}
                        }
                        return '';
                    }"""
                )
                if token:
                    logger.info("✓ 成功获取 Turnstile token")
                    break
                time.sleep(2)

            if not token:
                logger.warning("在限定时间内未获取到 Turnstile token（可能需要人工验证）")

    except Exception as e:
        logger.error(f"获取 Turnstile token 失败: {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    return token
