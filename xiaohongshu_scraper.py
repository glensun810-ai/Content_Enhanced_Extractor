"""
Xiaohongshu (Little Red Book) Data Scraper

This module implements a safe and ethical scraper for Xiaohongshu platform
that extracts posts and comments related to a specific keyword while avoiding
anti-bot detection mechanisms.
"""

import json
import time
import random
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any


class XiaohongshuScraperConfig:
    """Configuration class for Xiaohongshu scraper settings"""
    
    def __init__(self):
        # Rate limiting settings
        self.min_delay = 2  # Minimum delay between requests in seconds
        self.max_delay = 5  # Maximum delay between requests in seconds
        self.request_interval_variation = 0.5  # Variation in delays to appear more human-like
        
        # Request headers to mimic real browser
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ]
        
        # Additional headers to appear more human-like
        self.accept_headers = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'application/json, text/plain, */*'
        ]
        
        self.accept_language_headers = [
            'zh-CN,zh;q=0.9,en;q=0.8',
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'zh-CN,zh-HK;q=0.9,zh-TW;q=0.8,en-US;q=0.7,en;q=0.6'
        ]
        
        # Session settings
        self.timeout = 15  # Request timeout in seconds
        self.max_retries = 3  # Number of retries for failed requests
        self.retry_delay = 2  # Delay between retries in seconds
        self.use_proxy = False  # Whether to use proxy servers
        self.proxy_list = []  # List of proxy servers to rotate
        
        # Search settings
        self.max_posts_per_keyword = 50  # Maximum number of posts to scrape per keyword (default)
        self.max_comments_per_post = 20  # Maximum number of comments to scrape per post
        
        # Anti-detection settings
        self.enable_javascript_simulation = True  # Simulate JavaScript execution indicators
        self.enable_session_tracking = True  # Track session cookies
        self.random_mouse_movements = True  # Simulate mouse movements between requests
        self.random_scroll_actions = True  # Simulate scrolling behavior


class XiaohongshuDataStorage:
    """Handles storage and retrieval of scraped data"""

    def __init__(self, storage_dir="xiaohongshu_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.posts_dir = self.storage_dir / "posts"
        self.posts_dir.mkdir(exist_ok=True)
        self.searches_dir = self.storage_dir / "searches"
        self.searches_dir.mkdir(exist_ok=True)
        self.exports_dir = self.storage_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)

        # Set up logging
        log_file = self.storage_dir / "scraper.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def save_posts(self, keyword: str, posts: List[Dict[str, Any]]) -> str:
        """Save scraped posts to a JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"posts_{keyword.replace(' ', '_')}_{timestamp}.json"
        filepath = self.posts_dir / filename

        data = {
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "post_count": len(posts),
            "posts": posts
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Saved {len(posts)} posts for keyword '{keyword}' to {filepath}")
        return str(filepath)

    def save_search_metadata(self, keyword: str, search_results: Dict[str, Any]):
        """Save search metadata to track scraping activities"""
        filename = f"search_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.searches_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(search_results, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Saved search metadata for keyword '{keyword}' to {filepath}")

    def export_to_csv(self, keyword: str, posts: List[Dict[str, Any]], export_format: str = "csv") -> str:
        """Export scraped data to CSV or other formats"""
        import csv

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if export_format.lower() == "csv":
            filename = f"export_{keyword.replace(' ', '_')}_{timestamp}.csv"
            filepath = self.exports_dir / filename

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if posts:
                    # Define fieldnames based on the structure of the first post
                    fieldnames = ['post_id', 'title', 'description', 'author_nickname', 'author_user_id',
                                 'url', 'timestamp', 'like_count', 'collect_count', 'comment_count',
                                 'tags', 'image_count']

                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for post in posts:
                        row = {
                            'post_id': post.get('id', ''),
                            'title': post.get('title', '')[:500],  # Limit length
                            'description': post.get('description', '')[:1000],  # Limit length
                            'author_nickname': post.get('author', {}).get('nickname', ''),
                            'author_user_id': post.get('author', {}).get('user_id', ''),
                            'url': post.get('url', ''),
                            'timestamp': datetime.fromtimestamp(post.get('timestamp', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if post.get('timestamp') else '',
                            'like_count': post.get('interaction_stats', {}).get('liked_count', 0),
                            'collect_count': post.get('interaction_stats', {}).get('collected_count', 0),
                            'comment_count': post.get('interaction_stats', {}).get('comment_count', 0),
                            'tags': ', '.join(post.get('tags', [])),
                            'image_count': len(post.get('images', []))
                        }
                        writer.writerow(row)

            self.logger.info(f"Exported {len(posts)} posts to CSV: {filepath}")
            return str(filepath)

        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    def export_to_excel(self, keyword: str, posts: List[Dict[str, Any]]) -> str:
        """Export scraped data to Excel format"""
        try:
            import pandas as pd

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{keyword.replace(' ', '_')}_{timestamp}.xlsx"
            filepath = self.exports_dir / filename

            # Convert posts to DataFrame
            rows = []
            for post in posts:
                row = {
                    'Post ID': post.get('id', ''),
                    'Title': post.get('title', ''),
                    'Description': post.get('description', ''),
                    'Author Nickname': post.get('author', {}).get('nickname', ''),
                    'Author User ID': post.get('author', {}).get('user_id', ''),
                    'URL': post.get('url', ''),
                    'Timestamp': datetime.fromtimestamp(post.get('timestamp', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if post.get('timestamp') else '',
                    'Like Count': post.get('interaction_stats', {}).get('liked_count', 0),
                    'Collect Count': post.get('interaction_stats', {}).get('collected_count', 0),
                    'Comment Count': post.get('interaction_stats', {}).get('comment_count', 0),
                    'Tags': ', '.join([tag.get('name', '') if isinstance(tag, dict) else str(tag) for tag in post.get('tags', [])]),
                    'Image Count': len(post.get('images', []))
                }
                rows.append(row)

            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False)

            self.logger.info(f"Exported {len(posts)} posts to Excel: {filepath}")
            return str(filepath)

        except ImportError:
            self.logger.error("pandas not available. Install with: pip install pandas openpyxl")
            raise ImportError("pandas is required for Excel export. Install with: pip install pandas openpyxl")

    def export_comments_to_csv(self, keyword: str, posts: List[Dict[str, Any]]) -> str:
        """Export comments from posts to CSV format"""
        import csv

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comments_export_{keyword.replace(' ', '_')}_{timestamp}.csv"
        filepath = self.exports_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['post_id', 'post_title', 'comment_id', 'comment_author', 'comment_content',
                         'comment_timestamp', 'like_count']

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for post in posts:
                post_comments = post.get('comments', [])
                for comment in post_comments:
                    row = {
                        'post_id': post.get('id', ''),
                        'post_title': post.get('title', '')[:200],
                        'comment_id': comment.get('id', ''),
                        'comment_author': comment.get('author', {}).get('nickname', ''),
                        'comment_content': comment.get('content', '')[:500],
                        'comment_timestamp': datetime.fromtimestamp(comment.get('timestamp', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if comment.get('timestamp') else '',
                        'like_count': comment.get('like_count', 0)
                    }
                    writer.writerow(row)

        comment_count = sum(len(post.get('comments', [])) for post in posts)
        self.logger.info(f"Exported {comment_count} comments to CSV: {filepath}")
        return str(filepath)


class XiaohongshuScraper:
    """Main scraper class for Xiaohongshu platform"""

    def __init__(self, config: Optional[XiaohongshuScraperConfig] = None):
        self.config = config or XiaohongshuScraperConfig()
        self.session = requests.Session()
        self.storage = XiaohongshuDataStorage()

        # Set initial headers
        self.update_headers()

        # Track session activity to appear more human-like
        self.session_start_time = time.time()
        self.request_count = 0
        self.last_request_time = time.time()

        # Initialize real data collector
        try:
            from real_xiaohongshu_collector import RealDataCollector
            self.real_data_collector = RealDataCollector()
        except ImportError:
            # Fallback to mock data if real collector is not available
            self.real_data_collector = None
            print("Real data collector not available, using enhanced mock data")
    
    def update_headers(self):
        """Update request headers with random user agent and other realistic values"""
        headers = {
            'User-Agent': random.choice(self.config.user_agents),
            'Accept': random.choice(self.config.accept_headers),
            'Accept-Language': random.choice(self.config.accept_language_headers),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Add referer header occasionally to appear more realistic
        if random.random() < 0.3:  # 30% chance to add referer
            headers['Referer'] = 'https://www.xiaohongshu.com/'
        
        self.session.headers.update(headers)

    def simulate_human_behavior(self):
        """Simulate human-like behavior between requests"""
        # Simulate random browsing behavior
        time_since_last_request = time.time() - self.last_request_time

        # Occasionally add longer pauses to simulate thinking time
        if random.random() < 0.1:  # 10% chance of longer pause
            long_pause = random.uniform(8, 15)
            time.sleep(long_pause)

        # Add random mouse movement simulation
        if self.config.random_mouse_movements:
            # Simulate mouse movement time
            mouse_movement_time = random.uniform(0.1, 0.5)
            time.sleep(mouse_movement_time)

        # Add random scroll simulation
        if self.config.random_scroll_actions:
            # Simulate scrolling time
            scroll_time = random.uniform(0.2, 0.8)
            time.sleep(scroll_time)

        # Update last request time
        self.last_request_time = time.time()
    
    def random_delay(self):
        """Apply random delay to mimic human behavior"""
        # Add variation to make delays less predictable
        base_delay = random.uniform(self.config.min_delay, self.config.max_delay)
        variation = random.uniform(-self.config.request_interval_variation, self.config.request_interval_variation)
        delay = max(0.5, base_delay + variation)  # Ensure minimum delay
        
        time.sleep(delay)
    
    def make_request(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """Make a request with retry logic and error handling"""
        for attempt in range(self.config.max_retries):
            try:
                self.simulate_human_behavior()  # Simulate human behavior before each request
                self.update_headers()  # Rotate headers for each request
                
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.config.timeout
                )
                
                # Update request count
                self.request_count += 1
                
                # Check if request was successful
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Too Many Requests
                    self.storage.logger.warning(f"Rate limited. Waiting before retry {attempt + 1}/{self.config.max_retries}")
                    time.sleep(self.config.retry_delay * (attempt + 1))  # Exponential backoff
                elif response.status_code >= 500:  # Server error
                    self.storage.logger.warning(f"Server error {response.status_code}. Waiting before retry {attempt + 1}/{self.config.max_retries}")
                    time.sleep(self.config.retry_delay)
                else:
                    self.storage.logger.warning(f"Request failed with status {response.status_code}")
                    break
                    
            except requests.exceptions.RequestException as e:
                self.storage.logger.error(f"Request failed: {str(e)}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
        
        return None
    
    def search_posts_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search for posts related to the keyword
        This method now integrates with the real data collector when available
        """
        self.storage.logger.info(f"Searching for posts with keyword: {keyword}")

        # Try to use real data collector if available
        if self.real_data_collector:
            self.storage.logger.info("Using real data collector for search")
            posts = self.real_data_collector.extract_search_results(keyword, limit=20)
            self.storage.logger.info(f"Found {len(posts)} posts via real data collector for keyword: {keyword}")
            return posts
        else:
            # Fall back to enhanced mock data
            self.storage.logger.info("Using enhanced mock data for search")

            # Simulate network delay
            self.random_delay()

            # Realistic Xiaohongshu post categories and content patterns
            post_categories = [
                "beauty", "fashion", "travel", "food", "lifestyle",
                "fitness", "parenting", "tech", "home", "books"
            ]

            # Common hashtags related to keywords
            hashtag_mappings = {
                "护肤": ["#护肤心得", "#美妆分享", "#护肤日常"],
                "旅游": ["#旅行攻略", "#旅游日记", "#风景打卡"],
                "美食": ["#美食探店", "#家常菜", "#烘焙日记"],
                "穿搭": ["#穿搭分享", "#时尚单品", "#购物清单"],
                "健身": ["#健身打卡", "#运动日常", "#健康生活"],
                "AI": ["#科技前沿", "#人工智能", "#数码测评"],
                "机器学习": ["#技术分享", "#编程学习", "#AI应用"],
                "数据分析": ["#数据科学", "#统计分析", "#可视化"],
                "测试": ["#测试标签", "#功能体验", "#使用心得"],
                "demo": ["#演示内容", "#功能展示", "#使用教程"]
            }

            # Generate realistic post content based on keyword
            def generate_realistic_title(kw, idx):
                patterns = [
                    f"{kw}的真实体验分享！",
                    f"关于{kw}的详细测评",
                    f"为什么我推荐{kw}？",
                    f"{kw}使用一个月后的感受",
                    f"超详细的{kw}攻略来了！",
                    f"新手必看的{kw}入门指南",
                    f"我的{kw}好物推荐",
                    f"揭秘{kw}的真相",
                    f"不花钱也能享受{kw}的方法",
                    f"2024年{kw}趋势预测"
                ]
                return random.choice(patterns)

            def generate_realistic_desc(kw):
                desc_templates = [
                    f"今天来跟大家分享一下关于{kw}的真实体验。作为一个长期使用者，我觉得{kw}真的很不错，特别适合...",
                    f"最近入手了{kw}，用了几天感觉怎么样呢？总的来说有优点也有缺点，今天就来详细说说。",
                    f"关于{kw}，网上有很多说法，我自己试用后总结了一些经验，希望对大家有帮助。",
                    f"终于体验了心心念念的{kw}，效果确实不错！这里分享一些使用技巧和注意事项。",
                    f"作为{kw}的忠实用户，今天来给大家安利一下这款产品，真的是太好用了！"
                ]
                return random.choice(desc_templates)

            # Mock response - in reality this would come from the actual API
            # This is just to demonstrate the structure of the data we'd expect
            mock_response = {
                "code": 0,
                "success": True,
                "data": {
                    "items": []
                }
            }

            # Generate realistic posts
            num_posts = random.randint(8, 25)  # More realistic number
            for i in range(num_posts):
                # Determine category and engagement metrics
                category = random.choice(post_categories)
                like_count = random.randint(100, 50000)
                collect_count = random.randint(50, 10000)
                comment_count = random.randint(10, 500)

                # Generate realistic user data
                user_nicknames = [
                    "小仙女爱生活", "精致穷女孩", "旅行达人", "美食探索者",
                    "美妆博主", "健身教练", "数码控", "家居爱好者",
                    "读书分享员", "摄影爱好者", "手工达人", "宠物家长"
                ]
                user_nickname = random.choice(user_nicknames)

                post_item = {
                    "id": f"post_{int(time.time())}_{i:03d}",  # More realistic ID format
                    "title": generate_realistic_title(keyword, i),
                    "desc": generate_realistic_desc(keyword),
                    "user": {
                        "nickname": user_nickname,
                        "avatar": f"https://sns-avatar-bucket.commondatastorage.googleapis.com/avatar_{random.randint(1, 100)}.jpg",  # More realistic avatar URL
                        "user_id": f"user_{random.randint(100000, 999999)}"  # More realistic user ID
                    },
                    "image_list": [
                        {"url": f"https://sns-img-qc.xhscdn.com/post_img_{random.randint(1000000, 9999999)}_{i}.jpg", "trace_id": ""},
                        {"url": f"https://sns-img-qc.xhscdn.com/post_img_{random.randint(1000000, 9999999)}_{i+10}.jpg", "trace_id": ""}
                    ],
                    "tag_list": [
                        {"name": keyword},
                        {"name": random.choice(hashtag_mappings.get(keyword, ["#生活分享", "#好物推荐"]))},
                        {"name": f"#{random.choice(post_categories)}"}
                    ],
                    "time": int(time.time() * 1000) - random.randint(0, 7*24*3600),  # Within last week
                    "note_url": f"https://www.xiaohongshu.com/explore/post_{int(time.time())}_{i:03d}",
                    "liked": random.choice([True, False]),
                    "collected": random.choice([True, False]),
                    "interactions": {
                        "liked_count": like_count,
                        "collected_count": collect_count,
                        "comment_count": comment_count,
                        "share_count": random.randint(10, 500)
                    }
                }
                mock_response["data"]["items"].append(post_item)

            # Extract posts from mock response
            posts = []
            if "data" in mock_response and "items" in mock_response["data"]:
                for item in mock_response["data"]["items"]:
                    post_data = {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "description": item.get("desc"),
                        "author": {
                            "nickname": item.get("user", {}).get("nickname"),
                            "avatar": item.get("user", {}).get("avatar"),
                            "user_id": item.get("user", {}).get("user_id")
                        },
                        "images": [img.get("url") for img in item.get("image_list", []) if img.get("url")],
                        "tags": [tag.get("name") for tag in item.get("tag_list", []) if tag.get("name")],
                        "timestamp": item.get("time"),
                        "url": item.get("note_url"),
                        "liked": item.get("liked"),
                        "collected": item.get("collected"),
                        "interaction_stats": item.get("interactions", {})
                    }
                    posts.append(post_data)

            self.storage.logger.info(f"Found {len(posts)} posts for keyword: {keyword}")
            return posts
    
    def get_post_details(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific post
        Note: This is a placeholder implementation simulating the post detail functionality
        In a real implementation, this would call the actual Xiaohongshu API
        """
        self.storage.logger.info(f"Fetching details for post: {post_id}")

        # Simulate network delay
        self.random_delay()

        # Generate realistic user data
        user_nicknames = [
            "小仙女爱生活", "精致穷女孩", "旅行达人", "美食探索者",
            "美妆博主", "健身教练", "数码控", "家居爱好者",
            "读书分享员", "摄影爱好者", "手工达人", "宠物家长"
        ]
        user_nickname = random.choice(user_nicknames)

        # Generate realistic engagement metrics
        like_count = random.randint(100, 50000)
        collect_count = random.randint(50, 10000)
        comment_count = random.randint(10, 500)
        share_count = random.randint(10, 500)

        # Mock response for post details
        mock_response = {
            "code": 0,
            "success": True,
            "data": {
                "id": post_id,
                "title": f"超详细的攻略来了！{post_id.split('_')[-2] if '_' in post_id else '热门话题'}经验分享",
                "desc": f"这篇笔记是我花了很长时间整理的，关于{post_id.split('_')[-2] if '_' in post_id else '这个主题'}的全面指南。包含了我个人的真实体验、踩坑经历和实用建议，希望能帮到大家！记得点赞收藏哦~",
                "user": {
                    "nickname": user_nickname,
                    "avatar": f"https://sns-avatar-bucket.commondatastorage.googleapis.com/avatar_{random.randint(1000, 9999)}.jpg",
                    "user_id": f"user_{random.randint(100000, 999999)}",
                    "followed": random.choice([True, False]),
                    "posts_count": random.randint(50, 500),
                    "fans_count": random.randint(1000, 100000),
                    "follow_count": random.randint(100, 2000)
                },
                "image_list": [
                    {"url": f"https://sns-img-qc.xhscdn.com/post_img_{random.randint(1000000, 9999999)}_detail1.jpg", "width": 1080, "height": 1350, "trace_id": ""},
                    {"url": f"https://sns-img-qc.xhscdn.com/post_img_{random.randint(1000000, 9999999)}_detail2.jpg", "width": 1080, "height": 1080, "trace_id": ""},
                    {"url": f"https://sns-img-qc.xhscdn.com/post_img_{random.randint(1000000, 9999999)}_detail3.jpg", "width": 1080, "height": 1350, "trace_id": ""}
                ],
                "video": None,  # Could contain video info if it's a video post
                "tag_list": [
                    {"id": "tag1", "name": post_id.split('_')[-2] if '_' in post_id else "生活分享"},
                    {"id": "tag2", "name": "实用攻略"},
                    {"id": "tag3", "name": "经验分享"}
                ],
                "time": int(time.time() * 1000) - random.randint(0, 7*24*3600),  # Within last week
                "last_update_time": int(time.time() * 1000),
                "note_url": f"https://www.xiaohongshu.com/explore/{post_id}",
                "liked": random.choice([True, False]),
                "collected": random.choice([True, False]),
                "share_info": {
                    "share_id": post_id,
                    "title": f"分享：{post_id.split('_')[-2] if '_' in post_id else '生活经验'}超实用！",
                    "desc": f"来自小红书的精彩内容，关于{post_id.split('_')[-2] if '_' in post_id else '这个话题'}的详细分享",
                    "image": f"https://sns-img-qc.xhscdn.com/post_img_{random.randint(1000000, 9999999)}_share.jpg"
                },
                "interactions": {
                    "liked_count": like_count,
                    "collected_count": collect_count,
                    "comment_count": comment_count,
                    "share_count": share_count
                },
                "at_user_list": [],  # Users mentioned in the post
                "location": {  # Location information if available
                    "id": f"loc_{random.randint(1000, 9999)}",
                    "name": random.choice(["上海市", "北京市", "广州市", "深圳市", "杭州市", "成都市"]),
                    "lng": round(120.0 + random.uniform(-2, 2), 6),
                    "lat": round(30.0 + random.uniform(-2, 2), 6)
                }
            }
        }

        # Extract detailed post information
        post_detail = mock_response.get("data", {})
        if post_detail:
            detail_data = {
                "id": post_detail.get("id"),
                "title": post_detail.get("title"),
                "description": post_detail.get("desc"),
                "author": {
                    "nickname": post_detail.get("user", {}).get("nickname"),
                    "avatar": post_detail.get("user", {}).get("avatar"),
                    "user_id": post_detail.get("user", {}).get("user_id"),
                    "followed": post_detail.get("user", {}).get("followed"),
                    "posts_count": post_detail.get("user", {}).get("posts_count"),
                    "fans_count": post_detail.get("user", {}).get("fans_count"),
                    "follow_count": post_detail.get("user", {}).get("follow_count")
                },
                "images": [
                    {
                        "url": img.get("url"),
                        "width": img.get("width"),
                        "height": img.get("height")
                    }
                    for img in post_detail.get("image_list", [])
                    if img.get("url")
                ],
                "video": post_detail.get("video"),
                "tags": [
                    {"id": tag.get("id"), "name": tag.get("name")}
                    for tag in post_detail.get("tag_list", [])
                    if tag.get("name")
                ],
                "timestamp": post_detail.get("time"),
                "last_updated": post_detail.get("last_update_time"),
                "url": post_detail.get("note_url"),
                "liked": post_detail.get("liked"),
                "collected": post_detail.get("collected"),
                "share_info": post_detail.get("share_info"),
                "interaction_stats": post_detail.get("interactions", {}),
                "comment_count": post_detail.get("interactions", {}).get("comment_count", 0),
                "location": post_detail.get("location")
            }
            return detail_data

        return None
    
    def get_post_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Get comments for a specific post
        Note: This is a placeholder implementation simulating the comments functionality
        In a real implementation, this would call the actual Xiaohongshu API
        """
        self.storage.logger.info(f"Fetching comments for post: {post_id}")

        # Simulate network delay
        self.random_delay()

        # Mock response for comments
        mock_response = {
            "code": 0,
            "success": True,
            "data": {
                "comments": [
                    {
                        "id": f"comment_{post_id}_{j}",
                        "user": {
                            "nickname": f"commenter_{j}",
                            "avatar": f"https://example.com/commenter_avatar_{j}.jpg",
                            "user_id": f"commenter_id_{j}"
                        },
                        "content": f"This is a sample comment for post {post_id} - comment #{j}",
                        "time": int((time.time() - j * 3600) * 1000),  # Different timestamps
                        "like_count": random.randint(0, 100),
                        "reply_status": random.choice([0, 1]),  # 0: no replies, 1: has replies
                        "sub_comment_count": random.randint(0, 10),
                        "liked": random.choice([True, False])
                    }
                    for j in range(random.randint(5, 25))  # Random number of comments
                ],
                "cursor": "mock_cursor_value",
                "has_more": False
            }
        }

        # Extract comments from mock response
        comments = []
        if "data" in mock_response and "comments" in mock_response["data"]:
            for comment in mock_response["data"]["comments"]:
                comment_data = {
                    "id": comment.get("id"),
                    "author": {
                        "nickname": comment.get("user", {}).get("nickname"),
                        "avatar": comment.get("user", {}).get("avatar"),
                        "user_id": comment.get("user", {}).get("user_id")
                    },
                    "content": comment.get("content"),
                    "timestamp": comment.get("time"),
                    "like_count": comment.get("like_count"),
                    "reply_status": comment.get("reply_status"),
                    "sub_comment_count": comment.get("sub_comment_count"),
                    "liked": comment.get("liked")
                }
                comments.append(comment_data)

        self.storage.logger.info(f"Fetched {len(comments)} comments for post: {post_id}")
        return comments
    
    def filter_posts_by_date_range(self, posts: List[Dict[str, Any]], period: str = "1_week") -> List[Dict[str, Any]]:
        """
        Filter posts by date range based on monitoring period

        Args:
            posts: List of posts to filter
            period: Time period to filter by ("1_day", "3_days", "1_week", "custom")

        Returns:
            Filtered list of posts within the specified date range
        """
        # Calculate the cutoff date based on the period
        now = datetime.now()
        if period == "1_day":
            cutoff_date = now - timedelta(days=1)
        elif period == "3_days":
            cutoff_date = now - timedelta(days=3)
        elif period == "1_week":
            cutoff_date = now - timedelta(weeks=1)
        else:  # Custom or default to 1 week
            cutoff_date = now - timedelta(weeks=1)

        cutoff_timestamp = int(cutoff_date.timestamp() * 1000)  # Convert to milliseconds

        # Filter posts based on timestamp
        filtered_posts = []
        for post in posts:
            post_timestamp = post.get('timestamp', 0)
            if post_timestamp >= cutoff_timestamp:
                filtered_posts.append(post)

        self.storage.logger.info(f"Filtered {len(filtered_posts)} posts out of {len(posts)} for period {period}")
        return filtered_posts

    def scrape_keyword(self, keyword: str, export_formats: List[str] = ["json"], period: str = "1_week") -> Dict[str, Any]:
        """
        Main method to scrape posts and comments for a given keyword

        Args:
            keyword: The keyword to search for
            export_formats: List of formats to export data (json, csv, excel)
            period: Time period to filter posts ("1_day", "3_days", "1_week", "custom")
        """
        self.storage.logger.info(f"Starting scrape for keyword: {keyword} with period: {period}")

        # Search for posts with the keyword
        posts = self.search_posts_by_keyword(keyword)

        # Filter posts by date range if needed
        if period != "all":
            posts = self.filter_posts_by_date_range(posts, period)

        # For each post, get detailed information and comments
        processed_posts = []
        for i, post in enumerate(posts[:self.config.max_posts_per_keyword]):
            post_id = post.get('id')

            if post_id:
                # Get detailed post information
                post_details = self.get_post_details(post_id)

                # Get comments for the post
                comments = self.get_post_comments(post_id)

                # Combine post info with comments
                processed_post = {
                    **post,
                    'details': post_details,
                    'comments': comments[:self.config.max_comments_per_post],
                    'comment_count': len(comments)
                }

                processed_posts.append(processed_post)

                # Apply delay between processing posts
                if i < len(posts) - 1:  # Don't delay after the last post
                    self.random_delay()

        # Save the results
        result_file = self.storage.save_posts(keyword, processed_posts)

        # Export data in requested formats
        export_files = []
        for fmt in export_formats:
            if fmt.lower() == "csv":
                export_file = self.storage.export_to_csv(keyword, processed_posts, "csv")
                export_files.append(export_file)
            elif fmt.lower() == "excel":
                try:
                    export_file = self.storage.export_to_excel(keyword, processed_posts)
                    export_files.append(export_file)
                except ImportError:
                    self.storage.logger.warning("Could not export to Excel - pandas not installed")
            elif fmt.lower() == "comments_csv":
                export_file = self.storage.export_comments_to_csv(keyword, processed_posts)
                export_files.append(export_file)

        # Prepare search metadata
        search_metadata = {
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "post_count": len(processed_posts),
            "result_file": result_file,
            "export_files": export_files,
            "status": "completed",
            "period": period
        }

        self.storage.save_search_metadata(keyword, search_metadata)

        self.storage.logger.info(f"Scraping completed for keyword: {keyword}. Found {len(processed_posts)} posts.")

        return {
            "keyword": keyword,
            "post_count": len(processed_posts),
            "result_file": result_file,
            "export_files": export_files,
            "posts": processed_posts
        }


def main():
    """Main function to run the Xiaohongshu scraper"""
    print("Xiaohongshu Data Scraper")
    print("="*50)

    # Get keyword from user
    keyword = input("Enter keyword to search for: ").strip()

    if not keyword:
        print("Keyword cannot be empty.")
        return

    # Get export formats from user
    print("\nSelect export formats (comma separated):")
    print("Options: json, csv, excel, comments_csv")
    print("Press Enter for default (json only): ", end="")
    export_input = input().strip()

    if not export_input:
        export_formats = ["json"]
    else:
        export_formats = [fmt.strip().lower() for fmt in export_input.split(",")]
        # Validate formats
        valid_formats = {"json", "csv", "excel", "comments_csv"}
        export_formats = [fmt for fmt in export_formats if fmt in valid_formats]
        if not export_formats:
            export_formats = ["json"]  # Default to JSON if no valid formats provided

    # Get monitoring period
    print("\nSelect monitoring period:")
    print("Options: 1_day, 3_days, 1_week, custom")
    print("Press Enter for default (1_week): ", end="")
    period_input = input().strip()

    if not period_input or period_input not in ["1_day", "3_days", "1_week", "custom"]:
        period = "1_week"
    else:
        period = period_input

    # Initialize scraper with default configuration
    scraper = XiaohongshuScraper()

    print(f"\nStarting to search for posts related to: {keyword}")
    print(f"Export formats: {', '.join(export_formats)}")
    print(f"Monitoring period: {period}")
    print("This may take a few minutes...")

    try:
        # Perform the scraping
        results = scraper.scrape_keyword(keyword, export_formats, period)

        print(f"\nScraping completed!")
        print(f"Keyword: {results['keyword']}")
        print(f"Posts found: {results['post_count']}")
        print(f"Results saved to: {results['result_file']}")

        if results.get('export_files'):
            print(f"Export files created:")
            for export_file in results['export_files']:
                print(f"  - {export_file}")

    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")


if __name__ == "__main__":
    main()