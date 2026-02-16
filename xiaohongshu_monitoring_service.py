"""
Xiaohongshu Monitoring Service
Implements a service-oriented architecture for monitoring functionality
"""

import asyncio
import threading
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

from xiaohongshu_scraper import XiaohongshuScraper, XiaohongshuScraperConfig


class MonitoringStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class MonitoringConfig:
    keywords: List[str]
    monitoring_period: str  # "1_day", "3_days", "1_week", "custom"
    max_duration_minutes: int
    max_posts_per_keyword: int
    export_formats: List[str]


@dataclass
class MonitoringProgress:
    keyword: str
    posts_found: int
    total_expected: int
    percentage: float
    elapsed_time: float


@dataclass
class MonitoringResult:
    keyword: str
    posts_found: int
    success: bool
    error_message: Optional[str] = None
    posts: List[Dict[str, Any]] = None


class XiaohongshuMonitoringService:
    """
    Service class that encapsulates the monitoring functionality
    Provides a clean interface between the GUI and the scraping logic
    """

    def __init__(self):
        self.status = MonitoringStatus.IDLE
        self.current_task = None
        self.start_time = None
        self.config = None
        self.results = []
        self._lock = threading.Lock()  # For thread safety

        # Event callbacks
        self.on_status_change: Optional[Callable[[MonitoringStatus], None]] = None
        self.on_progress: Optional[Callable[[MonitoringProgress], None]] = None
        self.on_result: Optional[Callable[[MonitoringResult], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[List[MonitoringResult]], None]] = None
    
    def start_monitoring(self, config: MonitoringConfig) -> bool:
        """
        Start the monitoring process asynchronously
        """
        if self.status != MonitoringStatus.IDLE:
            return False
            
        self.status = MonitoringStatus.RUNNING
        self.config = config
        self.results = []
        self.start_time = time.time()
        
        # Notify status change
        if self.on_status_change:
            self.on_status_change(self.status)
        
        # Run in a separate thread to avoid blocking the UI
        self.current_task = threading.Thread(
            target=self._execute_monitoring,
            args=(config,),
            daemon=True
        )
        self.current_task.start()
        
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Stop the monitoring process
        """
        with self._lock:
            if self.status in [MonitoringStatus.IDLE, MonitoringStatus.COMPLETED, MonitoringStatus.ERROR]:
                return False

            self.status = MonitoringStatus.STOPPING

            # Notify status change
            if self.on_status_change:
                self.on_status_change(self.status)

            return True

    def cleanup(self):
        """
        Clean up resources used by the service
        """
        with self._lock:
            if self.current_task and self.current_task.is_alive():
                # In a real implementation, we might need to interrupt the thread
                # For now, we'll just wait for it to finish
                pass
            self.current_task = None
            self.results = []
            self.status = MonitoringStatus.IDLE
    
    def _execute_monitoring(self, config: MonitoringConfig):
        """
        Execute the monitoring process in a background thread
        """
        try:
            # Initialize scraper
            scraper_config = XiaohongshuScraperConfig()
            scraper_config.max_posts_per_keyword = config.max_posts_per_keyword
            scraper = XiaohongshuScraper(scraper_config)

            # Map GUI period options to scraper-compatible options
            period_mapping = {
                "1_day": "1_day",
                "3_days": "3_days",
                "1_week": "1_week",
                "custom": "1_week"  # Default to 1 week for custom
            }
            mapped_period = period_mapping.get(config.monitoring_period, "1_week")

            # Process each keyword
            for i, keyword in enumerate(config.keywords):
                # Check if we should stop (thread-safe check)
                with self._lock:
                    if self.status == MonitoringStatus.STOPPING:
                        break

                # Check if duration limit has been reached
                elapsed_time = time.time() - self.start_time
                if elapsed_time >= config.max_duration_minutes * 60:
                    if self.on_progress:
                        progress = MonitoringProgress(
                            keyword=keyword,
                            posts_found=0,
                            total_expected=0,
                            percentage=0,
                            elapsed_time=elapsed_time
                        )
                        self.on_progress(progress)
                    break

                try:
                    # Scrape posts for this keyword
                    results = scraper.scrape_keyword(
                        keyword,
                        export_formats=config.export_formats,
                        period=mapped_period
                    )

                    # Process results
                    posts = results.get('posts', [])

                    # Add keyword to each post for tracking
                    for post in posts:
                        post['matched_keyword'] = keyword

                    # Create result object
                    result = MonitoringResult(
                        keyword=keyword,
                        posts_found=len(posts),
                        success=True,
                        posts=posts
                    )

                    # Add to results (thread-safe)
                    with self._lock:
                        self.results.append(result)

                    # Notify progress
                    if self.on_result:
                        self.on_result(result)

                    # Calculate and notify progress
                    if self.on_progress:
                        total_expected = config.max_posts_per_keyword
                        percentage = min(100, (len(posts) / total_expected) * 100) if total_expected > 0 else 0
                        elapsed_time = time.time() - self.start_time

                        progress = MonitoringProgress(
                            keyword=keyword,
                            posts_found=len(posts),
                            total_expected=total_expected,
                            percentage=percentage,
                            elapsed_time=elapsed_time
                        )
                        self.on_progress(progress)

                except Exception as e:
                    # Handle error for this keyword
                    result = MonitoringResult(
                        keyword=keyword,
                        posts_found=0,
                        success=False,
                        error_message=str(e)
                    )
                    # Add to results (thread-safe)
                    with self._lock:
                        self.results.append(result)

                    if self.on_error:
                        self.on_error(f"Error processing keyword '{keyword}': {str(e)}")

            # Check final status (thread-safe)
            with self._lock:
                if self.status != MonitoringStatus.STOPPING:
                    self.status = MonitoringStatus.COMPLETED
                else:
                    self.status = MonitoringStatus.IDLE  # Reset to idle if stopped

        except Exception as e:
            # Set error status (thread-safe)
            with self._lock:
                self.status = MonitoringStatus.ERROR
            if self.on_error:
                self.on_error(f"Monitoring failed: {str(e)}")
        finally:
            # Notify completion
            if self.on_status_change:
                self.on_status_change(self.status)

            if self.status == MonitoringStatus.COMPLETED and self.on_complete:
                # Get a copy of results (thread-safe)
                with self._lock:
                    results_copy = self.results.copy()
                self.on_complete(results_copy)
    
    def get_status(self) -> MonitoringStatus:
        """
        Get the current monitoring status
        """
        return self.status
    
    def get_results(self) -> List[MonitoringResult]:
        """
        Get the monitoring results
        """
        return self.results.copy()
    
    def get_elapsed_time(self) -> float:
        """
        Get the elapsed time since monitoring started
        """
        if self.start_time:
            return time.time() - self.start_time
        return 0.0


class EventPublisher:
    """
    Simple event publishing system for decoupling components
    """
    
    def __init__(self):
        self._subscribers = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def publish(self, event_type: str, data: Any = None):
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logging.error(f"Error in event handler for {event_type}: {e}")


# Example usage:
if __name__ == "__main__":
    # Example of how to use the service
    service = XiaohongshuMonitoringService()
    
    # Set up event handlers
    def on_status_change(status):
        print(f"Status changed to: {status}")
    
    def on_progress(progress):
        print(f"Progress for {progress.keyword}: {progress.percentage:.1f}% ({progress.posts_found} posts)")
    
    def on_result(result):
        print(f"Completed keyword '{result.keyword}': {result.posts_found} posts found")
    
    def on_error(error):
        print(f"Error: {error}")
    
    def on_complete(results):
        print(f"Monitoring completed! Total results: {len(results)}")
    
    service.on_status_change = on_status_change
    service.on_progress = on_progress
    service.on_result = on_result
    service.on_error = on_error
    service.on_complete = on_complete
    
    # Configure and start monitoring
    config = MonitoringConfig(
        keywords=["AI", "机器学习", "数据分析"],
        monitoring_period="1_week",
        max_duration_minutes=60,
        max_posts_per_keyword=20,
        export_formats=["json"]
    )
    
    print("Starting monitoring...")
    service.start_monitoring(config)
    
    # Wait for completion
    import time
    while service.get_status() in [MonitoringStatus.RUNNING, MonitoringStatus.STOPPING]:
        time.sleep(1)
    
    print("Monitoring finished!")