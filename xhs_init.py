import asyncio
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# 配置信息
STATE_FILE = "xhs_state.json"  # 存储登录状态的文件名
TARGET_URL = "https://www.xiaohongshu.com/explore"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # macOS Chrome 路径


async def run_login_process():
    async with async_playwright() as p:
        # 1. 启动浏览器：使用本地 Chrome
        browser = await p.chromium.launch(
            headless=False,
            executable_path=CHROME_PATH,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # 2. 创建上下文：模拟一个真实的 Windows/Chrome 环境
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )

        # 3. 注入隐身插件
        stealth = Stealth()
        await stealth.apply_stealth_async(context)

        page = await context.new_page()

        print(f"\n[*] 正在打开小红书首页：{TARGET_URL}")
        await page.goto(TARGET_URL)

        print("\n[!] 操作提示：")
        print("    1. 请在弹出的浏览器窗口中点击【登录】。")
        print("    2. 建议使用【手机号验证码】或【小红书App扫码】。")
        print("    3. 如果弹出滑块验证，请手动完成。")
        print("    4. 登录成功进入个人主页后，请回到这里，程序会自动识别并保存。")

        # 4. 智能检测登录成功逻辑
        # 我们通过监测页面是否出现了只有登录后才有的特征元素（如“发布”按钮、头像或侧边栏）来判断
        try:
            # 持续等待直到以下任一情况发生：
            # a) 侧边栏出现发布按钮 (.publish-video)
            # b) 页面 URL 包含 /explore 或 /discovery
            # c) 出现了用户头像 (.avatar-wrapper)

            # 使用 wait_for_function 可以更灵活地监控多个特征
            await page.wait_for_function("""
                () => {
                    const hasPublishBtn = document.querySelector('.side-bar .publish-video');
                    const hasAvatar = document.querySelector('.avatar-wrapper') || document.querySelector('.user-info');
                    const isLoginedUrl = window.location.href.includes('/explore') || window.location.href.includes('/discovery');
                    return hasPublishBtn || hasAvatar || isLoginedUrl;
                }
            """, timeout=120000)  # 给用户 2 分钟时间完成登录

            print("\n[√] 成功检测到登录状态！")

            # 5. 额外等待 3 秒，确保所有加密 Cookie (如 a1, webId) 都已写入本地存储
            await asyncio.sleep(3)

            # 6. 保存状态到 JSON 文件
            await context.storage_state(path=STATE_FILE)
            print(f"\n[★] 成功！身份状态已保存至: {os.path.abspath(STATE_FILE)}")
            print("[*] 现在你可以关闭浏览器，并运行搜索脚本了。")

        except Exception as e:
            print(f"\n[x] 登录超时或发生错误。请确保你已完成登录。错误信息: {e}")
        finally:
            # 不要立即关闭，给用户一个确认的时间
            await asyncio.sleep(2)
            await browser.close()


if __name__ == "__main__":
    # 如果已存在状态文件，先提醒用户
    if os.path.exists(STATE_FILE):
        confirm = input(f"发现已存在的 {STATE_FILE}，重新登录将覆盖它。继续吗？(y/n): ")
        if confirm.lower() != 'y':
            exit()

    asyncio.run(run_login_process())