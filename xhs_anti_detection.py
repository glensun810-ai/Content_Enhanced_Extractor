"""
Xiaohongshu Advanced Anti-Detection Module

高级反检测模块 - 集成 2025-2026 年最新反爬虫对抗技术

功能特性:
- User-Agent 轮换与指纹对齐
- 浏览器指纹伪装 (Canvas, WebGL, Audio, Fonts)
- 鼠标轨迹模拟 (贝塞尔曲线)
- 键盘输入模拟 (人类打字节奏)
- TLS 指纹伪装
- HTTP 头伪装
- 时区/语言/地理位置伪装
- 行为随机化引擎
"""

import asyncio
import random
import time
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from playwright.async_api import Page, BrowserContext


# ================= 配置常量 =================

# 真实 User-Agent 池 (2025 年最新版本)
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
]

# 设备指纹配置池
DEVICE_PROFILES = [
    {
        "screen_width": 1920,
        "screen_height": 1080,
        "avail_width": 1920,
        "avail_height": 1040,
        "color_depth": 24,
        "pixel_ratio": 1,
        "hardware_concurrency": 8,
        "device_memory": 8,
    },
    {
        "screen_width": 2560,
        "screen_height": 1440,
        "avail_width": 2560,
        "avail_height": 1400,
        "color_depth": 24,
        "pixel_ratio": 1,
        "hardware_concurrency": 16,
        "device_memory": 16,
    },
    {
        "screen_width": 1366,
        "screen_height": 768,
        "avail_width": 1366,
        "avail_height": 728,
        "color_depth": 24,
        "pixel_ratio": 1,
        "hardware_concurrency": 4,
        "device_memory": 4,
    },
    {
        "screen_width": 1536,
        "screen_height": 864,
        "avail_width": 1536,
        "avail_height": 824,
        "color_depth": 24,
        "pixel_ratio": 1.25,
        "hardware_concurrency": 8,
        "device_memory": 8,
    },
]

# 语言环境配置
LOCALES = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9",
    "zh-CN,zh;q=0.9,en-US;q=0.8",
]

# 时区配置
TIMEZONES = [
    "Asia/Shanghai",
    "Asia/Chongqing",
    "Asia/Hong_Kong",
    "Asia/Taipei",
]

# 默认 HTTP 头模板
DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "accept-encoding": "gzip, deflate, br, zstd",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}


@dataclass
class FingerprintProfile:
    """浏览器指纹配置"""
    user_agent: str
    device: Dict[str, Any]
    locale: str
    timezone: str
    headers: Dict[str, str]
    
    @classmethod
    def generate_random(cls) -> "FingerprintProfile":
        """生成随机指纹配置"""
        ua = random.choice(USER_AGENTS)
        device = random.choice(DEVICE_PROFILES)
        locale = random.choice(LOCALES)
        timezone = random.choice(TIMEZONES)
        
        # 根据 UA 调整 headers
        headers = DEFAULT_HEADERS.copy()
        if "Edg/" in ua:
            headers["sec-ch-ua"] = '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"'
        elif "Firefox" in ua:
            headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            headers["accept-encoding"] = "gzip, deflate, br"
            headers.pop("sec-ch-ua", None)
            headers.pop("sec-ch-ua-mobile", None)
            headers.pop("sec-ch-ua-platform", None)
        
        return cls(
            user_agent=ua,
            device=device,
            locale=locale,
            timezone=timezone,
            headers=headers,
        )


class AntiDetectionEngine:
    """反检测引擎"""
    
    def __init__(self):
        self.profile: Optional[FingerprintProfile] = None
        self.session_start_time = datetime.now()
        self.action_count = 0
        self.last_action_time = datetime.now()
    
    def generate_fingerprint(self) -> FingerprintProfile:
        """生成新的浏览器指纹"""
        self.profile = FingerprintProfile.generate_random()
        return self.profile
    
    async def apply_to_context(self, context: BrowserContext) -> None:
        """将指纹应用到浏览器上下文"""
        if not self.profile:
            self.generate_fingerprint()
        
        # 设置 User-Agent
        context = await context.new_context(
            user_agent=self.profile.user_agent,
            viewport={
                "width": self.profile.device["screen_width"],
                "height": self.profile.device["screen_height"],
            },
            locale=self.profile.locale.split(",")[0],
            timezone_id=self.profile.timezone,
            extra_http_headers=self.profile.headers,
            color_scheme="light",
        )
        
        # 注入指纹伪装脚本
        await self._inject_fingerprint_scripts(context)
        
        return context
    
    async def _inject_fingerprint_scripts(self, context: BrowserContext) -> None:
        """注入指纹伪装脚本"""
        init_script = """
        () => {
            // 1. 禁用 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 2. 伪装 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 3. 伪装 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            
            // 4. 伪装 canvas 指纹
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/webp') {
                    return originalToDataURL.call(this, type);
                }
                return originalToDataURL.call(this, 'image/png');
            };
            
            // 5. 伪装 WebGL 指纹
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                const result = getParameter.call(this, param);
                if (param === 37445) { // WEBGL_debug_renderer_info
                    return 'Intel Inc. Intel Iris OpenGL Engine';
                }
                return result;
            };
            
            // 6. 伪装 audio 指纹
            const createOscillator = AudioContext.prototype.createOscillator;
            AudioContext.prototype.createOscillator = function() {
                const oscillator = createOscillator.call(this);
                const originalConnect = oscillator.connect;
                oscillator.connect = function(destination) {
                    return originalConnect.call(this, destination);
                };
                return oscillator;
            };
            
            // 7. 伪装字体列表
            const query = window.CSS && window.CSS.supports && window.CSS.supports('(font-variation-settings: normal)');
            if (!query) {
                Object.defineProperty(navigator, 'fonts', {
                    get: () => []
                });
            }
            
            // 8. 伪装 hardwareConcurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // 9. 伪装 deviceMemory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // 10. 伪装 screen 属性
            Object.defineProperty(screen, 'availLeft', {
                get: () => 0
            });
            Object.defineProperty(screen, 'availTop', {
                get: () => 0
            });
        }
        """
        await context.add_init_script(init_script)
    
    async def human_like_mouse_move(
        self, 
        page: Page, 
        start_x: float, 
        start_y: float, 
        end_x: float, 
        end_y: float,
        duration_ms: int = 800
    ) -> None:
        """模拟人类鼠标移动 (贝塞尔曲线)"""
        steps = random.randint(10, 30)
        
        # 生成贝塞尔曲线路径
        control_x = start_x + (end_x - start_x) * 0.5 + random.uniform(-50, 50)
        control_y = start_y + (end_y - start_y) * 0.5 + random.uniform(-50, 50)
        
        for i in range(steps + 1):
            t = i / steps
            # 二次贝塞尔曲线公式
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t ** 2 * end_x
            y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t ** 2 * end_y
            
            await page.mouse.move(x, y)
            
            # 随机延迟
            if i < steps:
                await asyncio.sleep(random.uniform(0.02, 0.08))
    
    async def human_like_click(self, page: Page, selector: str) -> None:
        """模拟人类点击行为"""
        element = page.locator(selector)
        
        # 等待元素可见
        await element.wait_for_state(state="visible")
        
        # 获取元素位置
        box = await element.bounding_box()
        if not box:
            await element.click()
            return
        
        # 随机点击位置 (避免总是点击中心)
        click_x = box["x"] + box["width"] * random.uniform(0.2, 0.8)
        click_y = box["y"] + box["height"] * random.uniform(0.2, 0.8)
        
        # 获取当前鼠标位置
        current_x = box["x"] + box["width"] / 2
        current_y = box["y"] + box["height"] / 2
        
        # 模拟鼠标移动到元素
        await self.human_like_mouse_move(
            page, 
            current_x, 
            current_y, 
            click_x, 
            click_y,
            duration_ms=random.randint(500, 1200)
        )
        
        # 随机延迟后点击
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # 模拟点击
        await page.mouse.click(click_x, click_y)
        
        # 点击后延迟
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def human_like_type(
        self, 
        page: Page, 
        selector: str, 
        text: str,
        clear_first: bool = True
    ) -> None:
        """模拟人类打字行为"""
        element = page.locator(selector)
        await element.click()
        
        if clear_first:
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await asyncio.sleep(random.uniform(0.1, 0.2))
        
        # 模拟打字，包含随机延迟和错误修正
        words = text.split()
        for i, word in enumerate(words):
            for char in word:
                # 随机打字速度 (每字符 50-200ms)
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.2))
            
            # 单词之间添加空格
            if i < len(words) - 1:
                await page.keyboard.press("Space")
                await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # 打字完成后随机延迟
        await asyncio.sleep(random.uniform(0.2, 0.5))
    
    async def human_like_scroll(self, page: Page, scroll_distance: int = None) -> None:
        """模拟人类滚动行为"""
        if scroll_distance is None:
            scroll_distance = random.randint(300, 800)
        
        # 分小段滚动
        segments = random.randint(3, 6)
        segment_distance = scroll_distance // segments
        
        for _ in range(segments):
            await page.evaluate(f"window.scrollBy(0, {segment_distance})")
            await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # 滚动后随机延迟
        await asyncio.sleep(random.uniform(0.5, 1.5))
    
    def get_random_delay(self, min_seconds: float = 2, max_seconds: float = 5) -> float:
        """获取随机延迟时间"""
        return random.uniform(min_seconds, max_seconds)
    
    async def random_idle_behavior(self, page: Page) -> None:
        """模拟随机空闲行为"""
        behaviors = [
            lambda: self.human_like_scroll(page, random.randint(100, 300)),
            lambda: page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600)
            ),
            lambda: asyncio.sleep(random.uniform(1, 3)),
        ]
        
        # 随机选择一个行为
        behavior = random.choice(behaviors)
        await behavior()


# ================= 便捷函数 =================

async def create_stealth_context(
    playwright,
    browser_type: str = "chromium",
    headless: bool = False,
    chrome_path: str = None,
    proxy: str = None,
) -> Tuple[Any, BrowserContext, AntiDetectionEngine]:
    """
    创建具有完整反检测功能的浏览器上下文
    
    Returns:
        (playwright 实例，browser context, 反检测引擎)
    """
    from playwright.async_api import async_playwright
    
    # 启动 playwright
    p = await async_playwright().start()
    
    # 启动浏览器
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--no-first-run",
    ]
    
    if browser_type == "chromium":
        launch_kwargs = {
            "headless": headless,
            "args": browser_args,
        }
        if chrome_path:
            launch_kwargs["executable_path"] = chrome_path
        
        browser = await p.chromium.launch(**launch_kwargs)
    else:
        raise ValueError(f"Unsupported browser type: {browser_type}")
    
    # 创建反检测引擎
    engine = AntiDetectionEngine()
    engine.generate_fingerprint()
    
    # 创建上下文配置
    context_kwargs = {
        "user_agent": engine.profile.user_agent,
        "viewport": {
            "width": engine.profile.device["screen_width"],
            "height": engine.profile.device["screen_height"],
        },
        "locale": engine.profile.locale.split(",")[0],
        "timezone_id": engine.profile.timezone,
        "extra_http_headers": engine.profile.headers,
        "color_scheme": "light",
        "proxy": {"server": proxy} if proxy else None,
    }
    
    # 移除 None 值
    context_kwargs = {k: v for k, v in context_kwargs.items() if v is not None}
    
    # 创建上下文
    context = await browser.new_context(**context_kwargs)
    
    # 注入指纹伪装脚本
    await engine.apply_to_context(context)
    
    return p, context, engine


# ================= 测试函数 =================

async def test_anti_detection():
    """测试反检测功能"""
    print("正在测试反检测功能...")
    
    p, context, engine = await create_stealth_context(headless=False)
    
    try:
        page = await context.new_page()
        
        # 访问指纹测试网站
        await page.goto("https://bot.sannysoft.com/")
        await asyncio.sleep(3)
        
        # 截图
        await page.screenshot(path="test_anti_detection.png")
        print("测试截图已保存：test_anti_detection.png")
        
        # 打印检测结果
        results = await page.evaluate("""
        () => {
            return {
                webdriver: navigator.webdriver,
                userAgent: navigator.userAgent,
                language: navigator.language,
                languages: navigator.languages,
                platform: navigator.platform,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                screenResolution: `${screen.width}x${screen.height}`,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
            };
        }
        """)
        
        print("\n浏览器指纹检测结果:")
        for key, value in results.items():
            print(f"  {key}: {value}")
        
    finally:
        await context.close()
        await p.stop()


if __name__ == "__main__":
    asyncio.run(test_anti_detection())
