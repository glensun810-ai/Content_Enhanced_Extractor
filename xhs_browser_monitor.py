"""
Xiaohongshu Browser-based Monitor

通过已登录的小红书网页版，搜索关键词并提取指定时间段内的帖子和评论。
支持手动登录后复用 session，实现合规的数据采集。

功能特性:
- 支持手动登录并保存登录状态
- 基于浏览器自动化搜索关键词
- 提取帖子和评论，包含时间戳过滤
- 支持多种时间周期过滤 (1 天，3 天，1 周，自定义)
- 数据导出为 JSON/CSV/Excel
- 集成高级反检测功能 (2025-2026 最新技术)
- 支持多账号管理和轮换
"""

import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

# 导入高级反检测模块
from xhs_anti_detection import AntiDetectionEngine, create_stealth_context
# 导入账号管理模块
from xhs_account_manager import AccountManager, AccountStatus


# ================= 配置区 =================
STATE_FILE = "xhs_browser_state.json"  # 登录状态文件
DATA_DIR = "xhs_browser_data"  # 数据存储目录

# macOS 本地 Chrome 浏览器路径
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class MonitorPeriod(Enum):
    """监控时间周期"""
    ONE_DAY = "1_day"
    THREE_DAYS = "3_days"
    ONE_WEEK = "1_week"
    TWO_WEEKS = "2_weeks"
    ONE_MONTH = "1_month"
    CUSTOM = "custom"


@dataclass
class PostData:
    """帖子数据结构"""
    id: str
    title: str
    description: str
    author_nickname: str
    author_id: str
    url: str
    timestamp: str  # ISO format
    timestamp_unix: int  # Unix timestamp in milliseconds
    like_count: int
    collect_count: int
    comment_count: int
    share_count: int
    tags: List[str]
    images: List[str]
    keyword: str  # 匹配的关键词
    extracted_at: str  # 提取时间


@dataclass
class CommentData:
    """评论数据结构"""
    id: str
    post_id: str
    post_title: str
    content: str
    author_nickname: str
    author_id: str
    timestamp: str
    timestamp_unix: int
    like_count: int
    keyword: str  # 匹配的关键词
    extracted_at: str


@dataclass
class MonitorConfig:
    """监控配置"""
    keywords: List[str]
    monitor_period: MonitorPeriod
    custom_days: int = 7  # 自定义天数
    max_posts_per_keyword: int = 50
    max_comments_per_post: int = 20
    extract_comments: bool = True
    headless: bool = False  # 是否无头模式


class BrowserController:
    """浏览器控制器 - 管理浏览器生命周期和登录状态

    集成 2025-2026 年最新反检测技术:
    - User-Agent 轮换
    - 浏览器指纹伪装
    - 鼠标/键盘行为模拟
    - TLS 指纹伪装
    - 多账号管理和轮换
    """

    def __init__(self, state_file: str = STATE_FILE, 
                 account_manager: Optional[AccountManager] = None):
        self.state_file = state_file
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        self.anti_detection = AntiDetectionEngine()
        self.account_manager = account_manager
        self.current_account_id: Optional[str] = None
        self.current_page: Optional[Page] = None

    async def init_browser(self, headless: bool = False) -> None:
        """初始化浏览器，使用高级反检测配置"""
        self.playwright = await async_playwright().start()

        # 使用增强的浏览器启动参数
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            executable_path=CHROME_PATH,
            args=[
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
                "--disable-blink-features=AutomationControlled",
            ]
        )

    async def create_context(self, account_id: str = None) -> BrowserContext:
        """
        创建浏览器上下文，应用完整的反检测指纹
        
        Args:
            account_id: 指定使用的账号 ID，None 则自动轮换
        """
        # 如果有账号管理器，获取账号
        if self.account_manager:
            if account_id:
                account = self.account_manager.get_account(account_id)
                self.current_account_id = account_id
            else:
                account = self.account_manager.get_next_account()
                if account:
                    self.current_account_id = account.account_id
            
            if self.current_account_id:
                # 使用该账号的状态文件
                self.state_file = self.account_manager.get_account_state_file(
                    self.current_account_id
                )
                print(f"[*] 使用账号：{account.username} (ID: {self.current_account_id})")
        
        # 生成随机指纹配置
        self.anti_detection.generate_fingerprint()

        print(f"[*] 使用 User-Agent: {self.anti_detection.profile.user_agent[:50]}...")
        print(f"[*] 时区：{self.anti_detection.profile.timezone}, 语言：{self.anti_detection.profile.locale}")

        if os.path.exists(self.state_file):
            # 加载已保存的登录状态
            self.context = await self.browser.new_context(
                storage_state=self.state_file,
                user_agent=self.anti_detection.profile.user_agent,
                viewport={
                    "width": self.anti_detection.profile.device["screen_width"],
                    "height": self.anti_detection.profile.device["screen_height"],
                },
                locale=self.anti_detection.profile.locale.split(",")[0],
                timezone_id=self.anti_detection.profile.timezone,
                extra_http_headers=self.anti_detection.profile.headers,
            )
            print("[*] 已加载本地登录状态。")
        else:
            # 创建新上下文
            self.context = await self.browser.new_context(
                user_agent=self.anti_detection.profile.user_agent,
                viewport={
                    "width": self.anti_detection.profile.device["screen_width"],
                    "height": self.anti_detection.profile.device["screen_height"],
                },
                locale=self.anti_detection.profile.locale.split(",")[0],
                timezone_id=self.anti_detection.profile.timezone,
                extra_http_headers=self.anti_detection.profile.headers,
            )
            print("[!] 未发现状态文件，需要手动登录。")

        # 应用 Stealth 隐身保护
        stealth = Stealth()
        await stealth.apply_stealth_async(self.context)
        
        # 注入指纹伪装脚本
        await self._inject_fingerprint_scripts()

        return self.context

    async def _inject_fingerprint_scripts(self) -> None:
        """注入浏览器指纹伪装脚本"""
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
            
            // 4. 伪装 hardwareConcurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // 5. 伪装 deviceMemory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // 6. 伪装 screen 属性
            Object.defineProperty(screen, 'availLeft', {
                get: () => 0
            });
            Object.defineProperty(screen, 'availTop', {
                get: () => 0
            });
            
            // 7. 伪装 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        }
        """
        await self.context.add_init_script(init_script)

    async def ensure_logged_in(self, page: Page, auto_login: bool = True) -> bool:
        """
        确保已登录，如未登录则尝试自动登录或等待用户手动登录

        Args:
            page: 浏览器页面
            auto_login: 是否尝试自动登录 (使用账号密码)

        Returns:
            bool: 是否登录成功
        """
        self.current_page = page

        # 检查是否已登录 (通过加载的 storage state)
        is_logged_in = await self._check_login_status(page)

        if is_logged_in:
            # 已登录，更新账号状态
            if self.account_manager and self.current_account_id:
                self.account_manager.update_account_status(
                    self.current_account_id,
                    AccountStatus.ACTIVE
                )
            print("[√] 登录状态有效。")
            return True

        # 未登录，尝试自动登录
        if auto_login and self.account_manager and self.current_account_id:
            print("\n[*] 检测到未登录状态，正在使用账号密码自动登录...")
            login_success = await self._auto_login(page)

            if login_success:
                print("[√] 自动登录成功!")
                await asyncio.sleep(3)  # 等待 Cookie 完全写入
                await self.context.storage_state(path=self.state_file)
                print(f"[★] 登录状态已保存至：{os.path.abspath(self.state_file)}")

                # 记录账号使用
                self.account_manager.record_usage(self.current_account_id)
                self.account_manager.update_account_status(
                    self.current_account_id,
                    AccountStatus.ACTIVE
                )
                return True
            else:
                print("[!] 自动登录失败，需要手动登录")

        # 自动登录失败或未启用，进入手动登录
        print("\n[!] 未检测到登录状态，请在弹出的浏览器窗口中完成登录...")
        print("[*] 建议使用手机号验证码或小红书 App 扫码登录")
        print("[*] 登录成功后会自动保存状态...")

        # 等待登录完成 (最多等待 120 秒)
        try:
            await page.wait_for_function("""
                () => {
                    const hasPublishBtn = document.querySelector('.side-bar .publish-video');
                    const hasAvatar = document.querySelector('.avatar-wrapper, .user-info');
                    return hasPublishBtn || hasAvatar;
                }
            """, timeout=120000)

            print("\n[√] 检测到登录成功!")
            await asyncio.sleep(3)  # 等待 Cookie 完全写入

            # 保存登录状态
            await self.context.storage_state(path=self.state_file)
            print(f"[★] 登录状态已保存至：{os.path.abspath(self.state_file)}")

            # 记录账号使用
            if self.account_manager and self.current_account_id:
                self.account_manager.record_usage(self.current_account_id)
                self.account_manager.update_account_status(
                    self.current_account_id,
                    AccountStatus.ACTIVE
                )

            return True

        except Exception as e:
            print(f"[x] 登录超时或失败：{e}")

            # 记录账号失败
            if self.account_manager and self.current_account_id:
                self.account_manager.update_account_status(
                    self.current_account_id,
                    AccountStatus.SUSPICIOUS,
                    str(e)
                )

            return False

    async def _auto_login(self, page: Page) -> bool:
        """
        使用账号密码自动登录
        
        注意：小红书可能有滑块验证，自动登录可能失败
        """
        try:
            if not self.account_manager or not self.current_account_id:
                return False
            
            # 获取账号密码
            account = self.account_manager.get_account(self.current_account_id)
            if not account:
                return False
            
            password = self.account_manager.get_password(self.current_account_id)
            
            # 打开登录页面
            print(f"    [*] 打开登录页面...")
            await page.goto("https://www.xiaohongshu.com/login")
            await asyncio.sleep(2)
            
            # 尝试找到登录表单
            # 注意：小红书的登录表单结构可能会变化
            try:
                # 切换到密码登录
                print(f"    [*] 输入账号：{account.username}")
                
                # 查找账号输入框 (可能需要根据实际页面调整选择器)
                try:
                    username_input = page.locator("input[type='text'], input[placeholder*='手机号']")
                    await username_input.wait_for(state="visible", timeout=5000)
                    await username_input.fill(account.username)
                except:
                    print("    [!] 未找到账号输入框，可能需要手动输入")
                    return False
                
                await asyncio.sleep(1)
                
                # 查找密码输入框
                try:
                    password_input = page.locator("input[type='password']")
                    await password_input.wait_for(state="visible", timeout=5000)
                    await password_input.fill(password)
                except:
                    print("    [!] 未找到密码输入框")
                    return False
                
                await asyncio.sleep(1)
                
                # 查找登录按钮
                try:
                    login_button = page.locator("button[type='submit'], .login-button")
                    await login_button.wait_for(state="visible", timeout=5000)
                    
                    # 使用拟人化点击
                    await self.anti_detection.human_like_click(page, "button[type='submit'], .login-button")
                except:
                    print("    [!] 未找到登录按钮")
                    return False
                
                # 等待登录结果
                print("    [*] 等待登录验证...")
                await asyncio.sleep(5)
                
                # 检查是否有滑块验证
                if await page.query_selector(".captcha"):
                    print("    [!] 检测到滑块验证，需要手动完成")
                    # 等待用户手动完成
                    try:
                        await page.wait_for_function("""
                            () => !document.querySelector('.captcha')
                        """, timeout=60000)
                    except:
                        print("    [x] 滑块验证超时")
                        return False
                
                # 检查是否登录成功
                return await self._check_login_status(page)
                
            except Exception as e:
                print(f"    [!] 自动登录过程出错：{e}")
                return False
        
        except Exception as e:
            print(f"    [!] 自动登录失败：{e}")
            return False

    async def _check_login_status(self, page: Page) -> bool:
        """检查登录状态"""
        try:
            # 检查登录特征元素
            await page.wait_for_selector(".side-bar .publish-video", timeout=5000)
            return True
        except:
            try:
                await page.wait_for_selector(".avatar-wrapper, .user-info", timeout=5000)
                return True
            except:
                return False

    async def close(self) -> None:
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class XiaohongshuBrowserMonitor:
    """小红书浏览器监控器 - 核心监控逻辑"""

    def __init__(self, config: MonitorConfig, 
                 account_manager: Optional[AccountManager] = None):
        self.config = config
        self.account_manager = account_manager
        self.controller = BrowserController(
            account_manager=account_manager
        )
        self.data_storage = DataStorage()

        # 计算时间范围
        self.time_range = self._calculate_time_range()

        # 统计信息
        self.stats = {
            "total_posts": 0,
            "total_comments": 0,
            "keywords_processed": 0,
            "start_time": None,
            "end_time": None
        }

    def _calculate_time_range(self) -> Tuple[datetime, datetime]:
        """计算监控时间范围"""
        end_time = datetime.now()
        
        if self.config.monitor_period == MonitorPeriod.ONE_DAY:
            start_time = end_time - timedelta(days=1)
        elif self.config.monitor_period == MonitorPeriod.THREE_DAYS:
            start_time = end_time - timedelta(days=3)
        elif self.config.monitor_period == MonitorPeriod.ONE_WEEK:
            start_time = end_time - timedelta(weeks=1)
        elif self.config.monitor_period == MonitorPeriod.TWO_WEEKS:
            start_time = end_time - timedelta(weeks=2)
        elif self.config.monitor_period == MonitorPeriod.ONE_MONTH:
            start_time = end_time - timedelta(days=30)
        elif self.config.monitor_period == MonitorPeriod.CUSTOM:
            start_time = end_time - timedelta(days=self.config.custom_days)
        else:
            start_time = end_time - timedelta(weeks=1)  # 默认 1 周
        
        return start_time, end_time

    async def search_keyword(self, keyword: str, page: Page) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """在小红书搜索关键词并提取结果 (使用拟人化行为)

        Returns:
            (帖子列表，评论列表) 元组
        """
        print(f"\n[*] 开始搜索关键词：{keyword}")

        try:
            # 先访问首页，模拟正常用户行为
            print("    [*] 访问小红书首页...")
            await page.goto("https://www.xiaohongshu.com/explore")
            await asyncio.sleep(random.uniform(3, 5))
            
            # 随机滚动，模拟浏览行为
            await self.controller.anti_detection.human_like_scroll(page, random.randint(200, 400))
            
            # 导航到搜索页面
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
            print(f"    [*] 搜索关键词：{keyword}")
            
            # 使用拟人化方式输入搜索关键词
            try:
                search_input = page.locator("input[type='text'], .search-input")
                await search_input.wait_for(state="visible", timeout=5000)
                await self.controller.anti_detection.human_like_type(page, "input[type='text'], .search-input", keyword)
                await page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(2, 4))
            except:
                # 如果找不到搜索框，直接跳转
                await page.goto(search_url)
                await asyncio.sleep(random.uniform(3, 5))

            # 滚动页面加载更多内容 (使用拟人化滚动)
            await self._scroll_to_load_more(page)

            # 提取搜索结果
            posts = await self._extract_search_results(page, keyword)

            # 过滤时间范围内的帖子
            filtered_posts = self._filter_posts_by_time(posts)

            print(f"[+] 找到 {len(filtered_posts)} 篇时间范围内的帖子")

            # 如果需要提取评论
            all_comments = []
            if self.config.extract_comments and filtered_posts:
                comments = await self._extract_comments_for_posts(filtered_posts, page)
                all_comments.extend(comments)
                self.stats["total_comments"] += len(comments)
                print(f"[+] 提取到 {len(comments)} 条评论")

            return filtered_posts, all_comments

        except Exception as e:
            print(f"[x] 搜索关键词 '{keyword}' 时出错：{e}")
            return [], []

    async def _scroll_to_load_more(self, page: Page, scroll_times: int = 3) -> None:
        """模拟人类滚动加载更多内容"""
        for i in range(scroll_times):
            # 使用拟人化滚动
            await self.controller.anti_detection.human_like_scroll(
                page, 
                scroll_distance=random.randint(300, 600)
            )

    async def _extract_search_results(self, page: Page, keyword: str) -> List[Dict[str, Any]]:
        """提取搜索结果"""
        posts = []
        
        try:
            # 查找所有笔记卡片
            note_items = await page.query_selector_all(".note-item")
            
            for idx, note in enumerate(note_items[:self.config.max_posts_per_keyword]):
                try:
                    # 提取标题
                    title_el = await note.query_selector(".title")
                    title = await title_el.inner_text() if title_el else ""
                    
                    # 提取作者
                    author_el = await note.query_selector(".author")
                    author = await author_el.inner_text() if author_el else ""
                    
                    # 提取链接
                    link_el = await note.query_selector("a.cover")
                    href = await link_el.get_attribute("href") if link_el else ""
                    url = f"https://www.xiaohongshu.com{href}" if href else ""
                    
                    # 提取互动数据
                    like_el = await note.query_selector(".like-count")
                    like_count = int(await like_el.inner_text()) if like_el else 0
                    
                    # 提取时间戳 (如果有)
                    timestamp_el = await note.query_selector(".time")
                    timestamp_str = await timestamp_el.inner_text() if timestamp_el else ""
                    timestamp_unix = self._parse_timestamp(timestamp_str)
                    
                    # 提取标签
                    tags_el = await note.query_selector_all(".tag")
                    tags = []
                    for tag_el in tags_el:
                        tag = await tag_el.inner_text()
                        if tag:
                            tags.append(tag)
                    
                    post_data = {
                        "id": f"xhs_{int(time.time())}_{idx:03d}",
                        "title": title,
                        "description": "",  # 搜索结果中通常不包含完整描述
                        "author_nickname": author,
                        "author_id": "",
                        "url": url,
                        "timestamp": timestamp_str,
                        "timestamp_unix": timestamp_unix,
                        "like_count": like_count,
                        "collect_count": 0,
                        "comment_count": 0,
                        "share_count": 0,
                        "tags": tags,
                        "images": [],
                        "keyword": keyword
                    }
                    
                    posts.append(post_data)
                    
                except Exception as e:
                    print(f"[!] 提取单条笔记时出错：{e}")
                    continue
                    
        except Exception as e:
            print(f"[x] 提取搜索结果时出错：{e}")
        
        return posts

    async def _extract_comments_for_posts(self, posts: List[Dict], page: Page) -> List[Dict[str, Any]]:
        """为帖子提取评论"""
        all_comments = []

        for post in posts[:self.config.max_posts_per_keyword]:
            try:
                # 导航到帖子详情页
                print(f"    [*] 提取评论：{post['title'][:30]}...")
                await page.goto(post["url"], timeout=30000)
                await asyncio.sleep(random.uniform(2, 4))

                # 检查页面是否有效（是否需要登录或页面不存在）
                try:
                    await page.wait_for_selector(".comment-area", timeout=5000)
                except:
                    print(f"    [!] 无法访问该帖子评论区，跳过...")
                    continue

                # 滚动加载评论
                await self._scroll_to_load_more(page, scroll_times=2)

                # 提取评论
                comments = await self._extract_comments(page, post)
                if comments:
                    all_comments.extend(comments)
                    print(f"    [+] 提取到 {len(comments)} 条评论")

                # 随机延迟，模拟人类行为
                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                print(f"    [!] 提取帖子评论时出错：{e}")
                continue

        return all_comments

    async def _extract_comments(self, page: Page, post: Dict) -> List[Dict[str, Any]]:
        """提取当前页面的评论"""
        comments = []
        
        try:
            comment_items = await page.query_selector_all(".comment-item")
            
            for idx, comment in enumerate(comment_items[:self.config.max_comments_per_post]):
                try:
                    # 提取评论内容
                    content_el = await comment.query_selector(".content")
                    content = await content_el.inner_text() if content_el else ""
                    
                    # 提取作者
                    author_el = await comment.query_selector(".username")
                    author = await author_el.inner_text() if author_el else ""
                    
                    # 提取时间
                    time_el = await comment.query_selector(".time")
                    time_str = await time_el.inner_text() if time_el else ""
                    timestamp_unix = self._parse_timestamp(time_str)
                    
                    # 提取点赞数
                    like_el = await comment.query_selector(".like-count")
                    like_count = int(await like_el.inner_text()) if like_el else 0
                    
                    comment_data = {
                        "id": f"comment_{int(time.time())}_{idx:03d}",
                        "post_id": post["id"],
                        "post_title": post["title"],
                        "content": content,
                        "author_nickname": author,
                        "author_id": "",
                        "timestamp": time_str,
                        "timestamp_unix": timestamp_unix,
                        "like_count": like_count,
                        "keyword": post["keyword"],
                        "extracted_at": datetime.now().isoformat()
                    }
                    
                    comments.append(comment_data)
                    
                except Exception as e:
                    print(f"[!] 提取单条评论时出错：{e}")
                    continue
                    
        except Exception as e:
            print(f"[x] 提取评论列表时出错：{e}")
        
        return comments

    def _filter_posts_by_time(self, posts: List[Dict]) -> List[Dict]:
        """根据时间范围过滤帖子"""
        start_timestamp = int(self.time_range[0].timestamp() * 1000)
        end_timestamp = int(self.time_range[1].timestamp() * 1000)
        
        filtered = []
        for post in posts:
            post_timestamp = post.get("timestamp_unix", 0)
            
            # 如果没有时间戳，尝试从文本解析
            if post_timestamp == 0 and post.get("timestamp"):
                post_timestamp = self._parse_timestamp(post["timestamp"])
            
            # 检查是否在时间范围内
            if start_timestamp <= post_timestamp <= end_timestamp:
                filtered.append(post)
            elif post_timestamp == 0:
                # 无法解析时间的帖子也保留 (可能是"刚刚"发布)
                filtered.append(post)
        
        return filtered

    def _parse_timestamp(self, timestamp_str: str) -> int:
        """解析时间字符串为 Unix 时间戳 (毫秒)"""
        if not timestamp_str:
            return 0
        
        now = datetime.now()
        
        # 处理相对时间
        if "刚刚" in timestamp_str:
            return int(now.timestamp() * 1000)
        elif "分钟前" in timestamp_str:
            try:
                minutes = int(timestamp_str.replace("分钟前", ""))
                return int((now - timedelta(minutes=minutes)).timestamp() * 1000)
            except:
                return 0
        elif "小时前" in timestamp_str:
            try:
                hours = int(timestamp_str.replace("小时前", ""))
                return int((now - timedelta(hours=hours)).timestamp() * 1000)
            except:
                return 0
        elif "天前" in timestamp_str:
            try:
                days = int(timestamp_str.replace("天前", ""))
                return int((now - timedelta(days=days)).timestamp() * 1000)
            except:
                return 0
        elif "昨天" in timestamp_str:
            return int((now - timedelta(days=1)).timestamp() * 1000)
        elif "前天" in timestamp_str:
            return int((now - timedelta(days=2)).timestamp() * 1000)
        
        # 尝试解析具体日期格式
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%m-%d",
            "%m/%d"
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(timestamp_str, fmt)
                # 如果是月 - 日格式，假设为今年
                if fmt in ["%m-%d", "%m/%d"]:
                    parsed = parsed.replace(year=now.year)
                return int(parsed.timestamp() * 1000)
            except:
                continue
        
        return 0

    async def run(self) -> Dict[str, Any]:
        """运行监控任务 (支持多账号轮换)"""
        self.stats["start_time"] = datetime.now().isoformat()

        print("\n" + "=" * 70)
        print("小红书浏览器监控器 - 多账号轮换版")
        print("=" * 70)
        print(f"监控时间范围：{self.time_range[0].strftime('%Y-%m-%d')} 至 {self.time_range[1].strftime('%Y-%m-%d')}")
        print(f"关键词列表：{self.config.keywords}")
        print(f"每关键词最大帖子数：{self.config.max_posts_per_keyword}")
        
        # 显示账号信息
        if self.account_manager:
            stats = self.account_manager.get_account_statistics()
            print(f"\n账号配置:")
            print(f"  总账号数：{stats.get('total', 0)}")
            print(f"  可用账号：{stats.get('total', 0) - stats.get('by_status', {}).get('banned', 0) - stats.get('by_status', {}).get('limited', 0)}")
            print(f"  冷却中：{stats.get('in_cooldown', 0)}")
            print(f"  轮换策略：启用 (冷却时间 1 小时)")
        else:
            print("\n账号配置：无 (使用手动登录)")
        
        print("=" * 70 + "\n")

        # 初始化浏览器
        await self.controller.init_browser(headless=self.config.headless)

        all_posts = []
        all_comments = []
        results = {}
        used_accounts = set()

        try:
            # 如果有账号管理器，使用账号轮换
            if self.account_manager:
                # 处理每个关键词
                for keyword_index, keyword in enumerate(self.config.keywords):
                    # 获取下一个可用账号
                    account = self.account_manager.get_account_for_search()
                    
                    if account:
                        print(f"\n[关键词 {keyword_index + 1}/{len(self.config.keywords)}]")
                        print(f"[*] 使用账号：{account.username} (ID: {account.account_id}, 已使用：{account.total_searches}次)")
                        
                        # 创建该账号的上下文
                        context = await self.controller.create_context(account.account_id)
                        page = await context.new_page()
                        
                        # 确保已登录 (尝试自动登录)
                        login_success = await self.controller.ensure_logged_in(page, auto_login=True)
                        
                        if login_success:
                            # 执行搜索
                            posts, comments = await self.search_keyword(keyword, page)
                            all_posts.extend(posts)
                            all_comments.extend(comments)
                            self.stats["total_posts"] += len(posts)
                            self.stats["keywords_processed"] += 1
                            
                            # 记录账号使用
                            self.account_manager.record_usage(account.account_id)
                            used_accounts.add(account.account_id)
                        else:
                            print(f"[!] 账号 {account.username} 登录失败，标记为可疑")
                            self.account_manager.update_account_status(
                                account.account_id, 
                                AccountStatus.SUSPICIOUS,
                                "登录失败"
                            )
                        
                        # 关闭页面
                        await page.close()
                    else:
                        print(f"[!] 没有可用账号，跳过关键词：{keyword}")
                    
                    # 关键词之间随机延迟
                    if keyword_index < len(self.config.keywords) - 1:
                        delay = random.uniform(5, 10)
                        print(f"[*] 等待 {delay:.1f} 秒后处理下一个关键词...")
                        await asyncio.sleep(delay)
            else:
                # 无账号管理器，使用单一账号 (手动登录)
                context = await self.controller.create_context()
                page = await context.new_page()
                
                # 确保已登录
                login_success = await self.controller.ensure_logged_in(page, auto_login=False)
                if not login_success:
                    print("[!] 登录失败，但将继续尝试搜索...")

                # 处理每个关键词
                for keyword in self.config.keywords:
                    try:
                        posts, comments = await self.search_keyword(keyword, page)
                        all_posts.extend(posts)
                        all_comments.extend(comments)
                        self.stats["total_posts"] += len(posts)
                        self.stats["keywords_processed"] += 1

                        # 关键词之间随机延迟
                        if keyword != self.config.keywords[-1]:
                            await asyncio.sleep(random.uniform(5, 10))
                    except Exception as e:
                        print(f"[!] 处理关键词 '{keyword}' 时出错：{e}，继续处理下一个关键词...")
                        continue

            # 保存结果
            results = {
                "posts": all_posts,
                "comments": all_comments,
                "stats": self.stats,
                "config": asdict(self.config),
                "time_range": {
                    "start": self.time_range[0].isoformat(),
                    "end": self.time_range[1].isoformat()
                }
            }

            # 导出数据
            export_path = await self.data_storage.save_results(results)
            print(f"\n[★] 结果已保存至：{export_path}")

            # 打印统计信息
            self._print_summary()
            
            # 打印账号使用统计
            if self.account_manager and used_accounts:
                print("\n账号使用统计:")
                for acc_id in used_accounts:
                    acc = self.account_manager.get_account(acc_id)
                    if acc:
                        print(f"  {acc.username}: 搜索 {acc.total_searches} 次")

            return results

        except KeyboardInterrupt:
            print("\n[!] 用户中断，保存已有结果...")
            results = {
                "posts": all_posts,
                "comments": all_comments,
                "stats": self.stats,
                "config": asdict(self.config),
                "time_range": {
                    "start": self.time_range[0].isoformat(),
                    "end": self.time_range[1].isoformat()
                }
            }
            export_path = await self.data_storage.save_results(results)
            print(f"[★] 结果已保存至：{export_path}")
            return results

        except Exception as e:
            print(f"\n[x] 运行过程中发生错误：{e}")
            # 即使出错也保存已有结果
            if all_posts or all_comments:
                results = {
                    "posts": all_posts,
                    "comments": all_comments,
                    "stats": self.stats,
                    "config": asdict(self.config),
                    "time_range": {
                        "start": self.time_range[0].isoformat(),
                        "end": self.time_range[1].isoformat()
                    }
                }
                export_path = await self.data_storage.save_results(results)
                print(f"[★] 部分结果已保存至：{export_path}")
            raise

        finally:
            self.stats["end_time"] = datetime.now().isoformat()
            await self.controller.close()

    def _print_summary(self) -> None:
        """打印监控摘要"""
        print("\n" + "=" * 60)
        print("监控摘要")
        print("=" * 60)
        print(f"开始时间：{self.stats['start_time']}")
        print(f"结束时间：{self.stats['end_time']}")
        print(f"处理关键词数：{self.stats['keywords_processed']}")
        print(f"找到帖子数：{self.stats['total_posts']}")
        print(f"找到评论数：{self.stats['total_comments']}")
        print("=" * 60)


class DataStorage:
    """数据存储类"""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.posts_dir = self.data_dir / "posts"
        self.posts_dir.mkdir(exist_ok=True)
        self.comments_dir = self.data_dir / "comments"
        self.comments_dir.mkdir(exist_ok=True)
        self.exports_dir = self.data_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)

    async def save_results(self, results: Dict[str, Any]) -> str:
        """保存监控结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存完整结果 JSON
        filename = f"monitor_result_{timestamp}.json"
        filepath = self.data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 导出 CSV
        if results["posts"]:
            csv_path = self.export_to_csv(results["posts"], "posts", timestamp)
            print(f"[+] 帖子 CSV 已导出：{csv_path}")
        
        if results["comments"]:
            csv_path = self.export_to_csv(results["comments"], "comments", timestamp)
            print(f"[+] 评论 CSV 已导出：{csv_path}")
        
        return str(filepath)

    def export_to_csv(self, data: List[Dict], data_type: str, timestamp: str) -> str:
        """导出数据为 CSV"""
        import csv
        
        filename = f"export_{data_type}_{timestamp}.csv"
        filepath = self.exports_dir / filename
        
        if not data:
            return str(filepath)
        
        # 确定字段
        if data_type == "posts":
            fieldnames = ['id', 'title', 'description', 'author_nickname', 'author_id',
                         'url', 'timestamp', 'like_count', 'collect_count', 'comment_count',
                         'share_count', 'tags', 'keyword', 'extracted_at']
        else:  # comments
            fieldnames = ['id', 'post_id', 'post_title', 'content', 'author_nickname',
                         'author_id', 'timestamp', 'like_count', 'keyword', 'extracted_at']
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        return str(filepath)


# ================= 便捷函数 =================

async def quick_monitor(
    keywords: List[str],
    period: str = "1_week",
    max_posts: int = 50,
    extract_comments: bool = True,
    headless: bool = False
) -> Dict[str, Any]:
    """
    快速启动监控
    
    Args:
        keywords: 关键词列表
        period: 时间周期 ("1_day", "3_days", "1_week", "2_weeks", "1_month")
        max_posts: 每关键词最大帖子数
        extract_comments: 是否提取评论
        headless: 是否无头模式
    
    Returns:
        监控结果字典
    """
    # 转换 period 字符串为枚举
    period_map = {
        "1_day": MonitorPeriod.ONE_DAY,
        "3_days": MonitorPeriod.THREE_DAYS,
        "1_week": MonitorPeriod.ONE_WEEK,
        "2_weeks": MonitorPeriod.TWO_WEEKS,
        "1_month": MonitorPeriod.ONE_MONTH
    }
    
    monitor_period = period_map.get(period, MonitorPeriod.ONE_WEEK)
    
    config = MonitorConfig(
        keywords=keywords,
        monitor_period=monitor_period,
        max_posts_per_keyword=max_posts,
        extract_comments=extract_comments,
        headless=headless
    )
    
    monitor = XiaohongshuBrowserMonitor(config)
    return await monitor.run()


# ================= 主程序入口 =================

async def main():
    """主程序入口"""
    print("\n" + "=" * 70)
    print("小红书浏览器监控器 - 多账号版")
    print("=" * 70)
    
    # 初始化账号管理器
    account_manager = AccountManager()
    
    # 检查是否有账号配置
    if not account_manager.accounts_file.exists():
        print("\n[!] 未检测到账号配置")
        print("\n请选择操作:")
        print("  1. 添加新账号")
        print("  2. 使用手动登录 (不保存账号)")
        
        choice = input("\n请输入选项 (1/2): ").strip()
        
        if choice == "1":
            # 设置主密码并添加账号
            account_manager.setup_master_password(new_password=True)
            
            while True:
                print(f"\n当前已添加 {len(account_manager.accounts)} 个账号")
                add_more = input("是否添加账号？(y/n): ").strip().lower()
                
                if add_more != 'y':
                    break
                
                username = input("请输入小红书账号 (手机号/邮箱): ").strip()
                password = getpass.getpass("请输入密码：")
                phone = input("请输入手机号 (可选): ").strip()
                notes = input("请输入备注 (可选): ").strip()
                
                account_manager.add_account(username, password, phone, notes)
            
            # 显示账号列表
            account_manager.print_accounts_summary()
        else:
            print("\n[*] 将使用手动登录模式")
            account_manager = None
    else:
        # 验证主密码
        password = account_manager.setup_master_password()
        if not password:
            print("[x] 主密码错误，退出程序")
            return
        
        # 显示账号列表
        account_manager.print_accounts_summary()
        
        # 选择账号
        print("\n请选择账号:")
        print("  0. 使用自动轮换")
        for acc_id, acc in account_manager.accounts.items():
            print(f"  {acc_id}. {acc.username} ({acc.status})")
        
        choice = input("\n请输入账号 ID (直接回车使用自动轮换): ").strip()
        
        if choice and choice != "0":
            if choice not in account_manager.accounts:
                print(f"[x] 账号不存在：{choice}")
                return
    
    # 示例配置
    config = MonitorConfig(
        keywords=["GEO 优化", "AI 搜索排名", "品牌获客"],
        monitor_period=MonitorPeriod.ONE_WEEK,
        max_posts_per_keyword=30,
        extract_comments=True,
        headless=False  # 有头模式，可以看到浏览器操作
    )

    # 创建监控器，传入账号管理器
    monitor = XiaohongshuBrowserMonitor(config, account_manager=account_manager)
    results = await monitor.run()

    return results


if __name__ == "__main__":
    import getpass
    asyncio.run(main())
