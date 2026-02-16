import asyncio
import random
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# ================= 配置区 =================
KEYWORDS = ["GEO优化", "AI搜索排名", "品牌获客"]  # 监控关键词列表
STATE_FILE = "xhs_state.json"  # 登录状态文件
LEADS_FILE = "xhs_leads_raw.json"  # 原始数据存储
LOOP_INTERVAL_MIN = 45  # 每次搜索的最小间隔(分钟)
LOOP_INTERVAL_MAX = 90  # 每次搜索的最大间隔(分钟)
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # macOS Chrome 路径


# ==========================================

class RedPulseSystem:
    def __init__(self):
        self.browser = None
        self.context = None

    async def init_browser(self, headless=False):
        """初始化具备隐身特征的浏览器"""
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(
            headless=headless,
            executable_path=CHROME_PATH,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # 创建 Stealth 实例
        stealth = Stealth()
        
        # 如果存在登录状态则加载
        if os.path.exists(STATE_FILE):
            self.context = await self.browser.new_context(
                storage_state=STATE_FILE
            )
            print("[*] 已加载本地登录状态。")
        else:
            self.context = await self.browser.new_context()
            print("[!] 未发现状态文件，准备进入手动登录模式...")

        # 应用隐身保护到上下文
        await stealth.apply_stealth_async(self.context)
        return p

    async def ensure_login(self):
        """闭环检测：确保账号处于登录状态"""
        page = await self.context.new_page()
        # Stealth is already applied at context level
        await page.goto("https://www.xiaohongshu.com/explore")

        try:
            # 检测登录特征元素（侧边栏发布按钮或头像）
            await page.wait_for_selector(".side-bar .publish-video", timeout=10000)
            print("[√] 登录状态有效。")
        except:
            print("[!] 状态失效或未登录，请在弹出的窗口中扫码...")
            # 如果没登录，则强制停留直到用户手动完成登录
            await page.wait_for_selector(".side-bar .publish-video", timeout=120000)
            await self.context.storage_state(path=STATE_FILE)
            print("[★] 登录成功，身份已同步至本地。")

        await page.close()

    async def human_like_search(self, keyword):
        """拟人化搜索逻辑核心"""
        page = await self.context.new_page()
        # Stealth is already applied at context level

        try:
            # 1. 模拟进入首页并停留
            await page.goto("https://www.xiaohongshu.com/explore")
            await asyncio.sleep(random.uniform(2, 5))

            # 2. 模拟点击搜索框并输入（逐字输入）
            search_input = page.locator(".search-input")
            await search_input.click()
            for char in keyword:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.1, 0.4))
            await page.keyboard.press("Enter")

            # 等待搜索结果加载
            await page.wait_for_selector(".note-item", timeout=10000)
            await asyncio.sleep(random.uniform(3, 6))

            # 3. 提取结果
            notes = await page.locator(".note-item").all()
            found_data = []

            # 只取前 8 条，模拟人类只看第一屏的习惯
            for i, note in enumerate(notes[:8]):
                try:
                    title_el = note.locator(".title")
                    author_el = note.locator(".author")
                    link_el = note.locator("a.cover")

                    item = {
                        "keyword": keyword,
                        "title": await title_el.inner_text(),
                        "author": await author_el.inner_text(),
                        "url": "https://www.xiaohongshu.com" + await link_el.get_attribute("href"),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    found_data.append(item)
                except:
                    continue

            # 4. 关键避障动作：随机点击一条笔记阅读，模拟真实兴趣
            if notes:
                target_index = random.randint(0, min(3, len(notes) - 1))
                print(f"[*] 模拟点击第 {target_index + 1} 条笔记进行深度阅读...")
                await notes[target_index].click()
                await asyncio.sleep(random.uniform(15, 30))  # 模拟阅读时间
                await page.go_back()

            return found_data

        except Exception as e:
            print(f"[x] 搜索 '{keyword}' 时发生异常: {e}")
            return []
        finally:
            # 每次操作完更新一下状态文件，保持 Cookie 活跃
            await self.context.storage_state(path=STATE_FILE)
            await page.close()

    def save_results(self, data):
        """保存线索到本地 JSON"""
        if not data: return

        existing_data = []
        if os.path.exists(LEADS_FILE):
            with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except:
                    pass

        # 去重保存
        existing_urls = {item['url'] for item in existing_data}
        new_items = [d for d in data if d['url'] not in existing_urls]

        existing_data.extend(new_items)
        with open(LEADS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        print(f"[+] 本次新增 {len(new_items)} 条原始线索。")


async def main_loop():
    system = RedPulseSystem()
    playwright_instance = await system.init_browser(headless=False)

    try:
        # 第一步：闭环鉴权
        await system.ensure_login()

        while True:
            # 第二步：随机选取一个关键词进行脉冲搜索
            kw = random.choice(KEYWORDS)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始脉冲搜索: {kw}")

            results = await system.human_like_search(kw)
            system.save_results(results)

            # 第三步：随机冷却，彻底打乱机器节奏
            wait_time = random.randint(LOOP_INTERVAL_MIN, LOOP_INTERVAL_MAX)
            print(f"[*] 任务完成。进入安全冷却期: {wait_time} 分钟...")
            await asyncio.sleep(wait_time * 60)

    except KeyboardInterrupt:
        print("[-] 系统手动停止。")
    finally:
        await playwright_instance.stop()


if __name__ == "__main__":
    asyncio.run(main_loop())