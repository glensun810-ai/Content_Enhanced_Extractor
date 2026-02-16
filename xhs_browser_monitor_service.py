"""
Xiaohongshu Browser Monitoring Service

为 GUI 界面提供浏览器监控服务的封装层
支持异步执行、进度回调和状态管理
"""

import asyncio
import threading
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

from xhs_browser_monitor import (
    XiaohongshuBrowserMonitor,
    MonitorConfig,
    MonitorPeriod,
    DataStorage,
    PostData,
    CommentData
)


class BrowserMonitorStatus(Enum):
    """浏览器监控器状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    WAITING_LOGIN = "waiting_login"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class BrowserMonitorProgress:
    """浏览器监控进度"""
    status: BrowserMonitorStatus
    keyword: str
    current_keyword_index: int
    total_keywords: int
    posts_found: int
    comments_found: int
    message: str
    percentage: float


@dataclass
class BrowserMonitorResult:
    """浏览器监控结果"""
    success: bool
    posts: List[Dict[str, Any]]
    comments: List[Dict[str, Any]]
    stats: Dict[str, Any]
    error_message: Optional[str] = None
    export_path: Optional[str] = None


class XiaohongshuBrowserMonitorService:
    """
    小红书浏览器监控服务
    
    为 GUI 提供友好的接口，封装浏览器监控的复杂性
    支持异步执行、进度回调和状态管理
    """

    def __init__(self):
        self.status = BrowserMonitorStatus.IDLE
        self.monitor: Optional[XiaohongshuBrowserMonitor] = None
        self.config: Optional[MonitorConfig] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        
        # 结果存储
        self.results: Optional[BrowserMonitorResult] = None
        
        # 事件回调
        self.on_status_change: Optional[Callable[[BrowserMonitorStatus], None]] = None
        self.on_progress: Optional[Callable[[BrowserMonitorProgress], None]] = None
        self.on_result: Optional[Callable[[BrowserMonitorResult], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[BrowserMonitorResult], None]] = None

    def start_monitoring(
        self,
        keywords: List[str],
        monitor_period: str = "1_week",
        custom_days: int = 7,
        max_posts_per_keyword: int = 50,
        max_comments_per_post: int = 20,
        extract_comments: bool = True,
        headless: bool = False
    ) -> bool:
        """
        启动监控任务
        
        Args:
            keywords: 关键词列表
            monitor_period: 监控周期 ("1_day", "3_days", "1_week", "2_weeks", "1_month", "custom")
            custom_days: 自定义天数 (当 monitor_period="custom" 时使用)
            max_posts_per_keyword: 每关键词最大帖子数
            max_comments_per_post: 每帖子最大评论数
            extract_comments: 是否提取评论
            headless: 是否无头模式
        
        Returns:
            是否成功启动
        """
        if self.status not in [BrowserMonitorStatus.IDLE, BrowserMonitorStatus.COMPLETED, 
                                BrowserMonitorStatus.ERROR, BrowserMonitorStatus.STOPPED]:
            return False
        
        # 转换 period 字符串为枚举
        period_map = {
            "1_day": MonitorPeriod.ONE_DAY,
            "3_days": MonitorPeriod.THREE_DAYS,
            "1_week": MonitorPeriod.ONE_WEEK,
            "2_weeks": MonitorPeriod.TWO_WEEKS,
            "1_month": MonitorPeriod.ONE_MONTH,
            "custom": MonitorPeriod.CUSTOM
        }
        
        monitor_period_enum = period_map.get(monitor_period, MonitorPeriod.ONE_WEEK)
        
        # 创建配置
        self.config = MonitorConfig(
            keywords=keywords,
            monitor_period=monitor_period_enum,
            custom_days=custom_days,
            max_posts_per_keyword=max_posts_per_keyword,
            max_comments_per_post=max_comments_per_post,
            extract_comments=extract_comments,
            headless=headless
        )
        
        # 重置状态
        self.status = BrowserMonitorStatus.INITIALIZING
        self._stop_requested = False
        self.results = None
        
        # 通知状态变化
        self._notify_status_change()
        
        # 在新线程中运行异步任务
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
        
        return True

    def stop_monitoring(self) -> bool:
        """停止监控任务"""
        if self.status in [BrowserMonitorStatus.IDLE, BrowserMonitorStatus.COMPLETED, 
                           BrowserMonitorStatus.ERROR, BrowserMonitorStatus.STOPPED]:
            return False
        
        self._stop_requested = True
        self.status = BrowserMonitorStatus.STOPPED
        self._notify_status_change()
        
        return True

    def _run_async_loop(self):
        """运行异步事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._execute_monitoring())
        except Exception as e:
            self._handle_error(f"监控执行失败：{str(e)}")
        finally:
            self._loop.close()

    async def _execute_monitoring(self):
        """执行监控任务"""
        try:
            # 创建监控器
            self.monitor = XiaohongshuBrowserMonitor(self.config)
            
            # 重写内部方法以发送进度更新
            original_search = self.monitor.search_keyword
            
            async def wrapped_search(keyword: str, page):
                if self._stop_requested:
                    return []
                
                # 更新状态
                self.status = BrowserMonitorStatus.SEARCHING
                self._notify_status_change()
                
                # 发送进度更新
                progress = BrowserMonitorProgress(
                    status=self.status,
                    keyword=keyword,
                    current_keyword_index=self.monitor.stats["keywords_processed"] + 1,
                    total_keywords=len(self.config.keywords),
                    posts_found=self.monitor.stats["total_posts"],
                    comments_found=self.monitor.stats["total_comments"],
                    message=f"正在搜索：{keyword}",
                    percentage=(self.monitor.stats["keywords_processed"] / len(self.config.keywords)) * 100
                )
                self._notify_progress(progress)
                
                return await original_search(keyword, page)
            
            self.monitor.search_keyword = wrapped_search
            
            # 执行监控
            results_dict = await self.monitor.run()
            
            if self._stop_requested:
                return
            
            # 更新状态
            self.status = BrowserMonitorStatus.SAVING
            self._notify_status_change()
            
            # 创建结果对象
            self.results = BrowserMonitorResult(
                success=True,
                posts=results_dict.get("posts", []),
                comments=results_dict.get("comments", []),
                stats=results_dict.get("stats", {}),
                export_path=results_dict.get("export_path")
            )
            
            # 完成
            self.status = BrowserMonitorStatus.COMPLETED
            self._notify_status_change()
            self._notify_complete()
            
        except Exception as e:
            self._handle_error(f"监控执行失败：{str(e)}")

    def _notify_status_change(self):
        """通知状态变化"""
        if self.on_status_change:
            self.on_status_change(self.status)

    def _notify_progress(self, progress: BrowserMonitorProgress):
        """通知进度更新"""
        if self.on_progress:
            self.on_progress(progress)

    def _notify_complete(self):
        """通知完成"""
        if self.on_complete and self.results:
            self.on_complete(self.results)

    def _handle_error(self, error_message: str):
        """处理错误"""
        self.status = BrowserMonitorStatus.ERROR
        self.results = BrowserMonitorResult(
            success=False,
            posts=[],
            comments=[],
            stats={},
            error_message=error_message
        )
        
        self._notify_status_change()
        
        if self.on_error:
            self.on_error(error_message)

    def get_status(self) -> BrowserMonitorStatus:
        """获取当前状态"""
        return self.status

    def get_results(self) -> Optional[BrowserMonitorResult]:
        """获取结果"""
        return self.results

    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self.monitor = None
        self.config = None
        self._loop = None
        self._task = None
        self._thread = None


# ================= GUI 集成辅助函数 =================

def get_period_options() -> List[Dict[str, str]]:
    """获取监控周期选项 (用于 GUI 下拉框)"""
    return [
        {"label": "最近 1 天", "value": "1_day"},
        {"label": "最近 3 天", "value": "3_days"},
        {"label": "最近 1 周", "value": "1_week"},
        {"label": "最近 2 周", "value": "2_weeks"},
        {"label": "最近 1 个月", "value": "1_month"},
        {"label": "自定义", "value": "custom"}
    ]


def format_status_message(status: BrowserMonitorStatus) -> str:
    """格式化状态消息 (用于 GUI 显示)"""
    messages = {
        BrowserMonitorStatus.IDLE: "空闲",
        BrowserMonitorStatus.INITIALIZING: "正在初始化...",
        BrowserMonitorStatus.WAITING_LOGIN: "等待用户登录...",
        BrowserMonitorStatus.SEARCHING: "正在搜索...",
        BrowserMonitorStatus.EXTRACTING: "正在提取数据...",
        BrowserMonitorStatus.SAVING: "正在保存结果...",
        BrowserMonitorStatus.COMPLETED: "已完成",
        BrowserMonitorStatus.ERROR: "错误",
        BrowserMonitorStatus.STOPPED: "已停止"
    }
    return messages.get(status, "未知状态")


def format_progress_message(progress: BrowserMonitorProgress) -> str:
    """格式化进度消息 (用于 GUI 显示)"""
    return (
        f"[{progress.current_keyword_index}/{progress.total_keywords}] "
        f"{progress.message} - "
        f"帖子：{progress.posts_found}, 评论：{progress.comments_found}"
    )


# ================= 使用示例 =================

if __name__ == "__main__":
    # 示例：如何使用服务
    service = XiaohongshuBrowserMonitorService()
    
    # 设置回调
    def on_status_change(status):
        print(f"状态变化：{format_status_message(status)}")
    
    def on_progress(progress):
        print(f"进度：{format_progress_message(progress)}")
    
    def on_error(error):
        print(f"错误：{error}")
    
    def on_complete(result):
        print(f"完成！找到 {len(result.posts)} 篇帖子，{len(result.comments)} 条评论")
        if result.export_path:
            print(f"结果已保存至：{result.export_path}")
    
    service.on_status_change = on_status_change
    service.on_progress = on_progress
    service.on_error = on_error
    service.on_complete = on_complete
    
    # 启动监控
    print("启动监控...")
    service.start_monitoring(
        keywords=["GEO 优化", "AI 搜索"],
        monitor_period="1_week",
        max_posts_per_keyword=20,
        extract_comments=True,
        headless=False
    )
    
    # 等待完成 (在实际 GUI 中不需要这样轮询)
    import time
    while service.get_status() not in [BrowserMonitorStatus.COMPLETED, 
                                        BrowserMonitorStatus.ERROR,
                                        BrowserMonitorStatus.STOPPED]:
        time.sleep(1)
    
    print("监控结束!")
