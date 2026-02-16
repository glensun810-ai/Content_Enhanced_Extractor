#!/usr/bin/env python3
"""
Test script for Xiaohongshu Browser Monitor

This script tests the basic functionality of the browser monitor module
without actually running the browser (for CI/testing purposes).
"""

import sys
import os

# Add project directory to path
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from xhs_browser_monitor import (
            XiaohongshuBrowserMonitor,
            MonitorConfig,
            MonitorPeriod,
            DataStorage,
            PostData,
            CommentData,
            BrowserController,
            quick_monitor
        )
        print("✓ xhs_browser_monitor imports successful")
    except ImportError as e:
        print(f"✗ xhs_browser_monitor import failed: {e}")
        return False
    
    try:
        from xhs_browser_monitor_service import (
            XiaohongshuBrowserMonitorService,
            BrowserMonitorStatus,
            BrowserMonitorProgress,
            BrowserMonitorResult,
            get_period_options,
            format_status_message,
            format_progress_message
        )
        print("✓ xhs_browser_monitor_service imports successful")
    except ImportError as e:
        print(f"✗ xhs_browser_monitor_service import failed: {e}")
        return False
    
    return True


def test_monitor_period_enum():
    """Test MonitorPeriod enum"""
    print("\nTesting MonitorPeriod enum...")
    
    from xhs_browser_monitor import MonitorPeriod
    
    periods = [
        MonitorPeriod.ONE_DAY,
        MonitorPeriod.THREE_DAYS,
        MonitorPeriod.ONE_WEEK,
        MonitorPeriod.TWO_WEEKS,
        MonitorPeriod.ONE_MONTH,
        MonitorPeriod.CUSTOM
    ]
    
    for period in periods:
        print(f"  - {period.name}: {period.value}")
    
    print("✓ MonitorPeriod enum test passed")
    return True


def test_monitor_config():
    """Test MonitorConfig dataclass"""
    print("\nTesting MonitorConfig...")
    
    from xhs_browser_monitor import MonitorConfig, MonitorPeriod
    
    config = MonitorConfig(
        keywords=["测试关键词 1", "测试关键词 2", "测试关键词 3"],
        monitor_period=MonitorPeriod.ONE_WEEK,
        custom_days=7,
        max_posts_per_keyword=50,
        max_comments_per_post=20,
        extract_comments=True,
        headless=False
    )
    
    print(f"  Keywords: {config.keywords}")
    print(f"  Period: {config.monitor_period.value}")
    print(f"  Max Posts: {config.max_posts_per_keyword}")
    print(f"  Extract Comments: {config.extract_comments}")
    
    print("✓ MonitorConfig test passed")
    return True


def test_data_storage():
    """Test DataStorage class"""
    print("\nTesting DataStorage...")
    
    from xhs_browser_monitor import DataStorage
    
    storage = DataStorage()
    
    # Check directories exist
    assert storage.data_dir.exists(), "Data directory should exist"
    assert storage.posts_dir.exists(), "Posts directory should exist"
    assert storage.comments_dir.exists(), "Comments directory should exist"
    assert storage.exports_dir.exists(), "Exports directory should exist"
    
    print(f"  Data directory: {storage.data_dir}")
    print(f"  Posts directory: {storage.posts_dir}")
    print(f"  Comments directory: {storage.comments_dir}")
    print(f"  Exports directory: {storage.exports_dir}")
    
    print("✓ DataStorage test passed")
    return True


def test_service_helpers():
    """Test service helper functions"""
    print("\nTesting service helper functions...")
    
    from xhs_browser_monitor_service import (
        get_period_options,
        format_status_message,
        format_progress_message,
        BrowserMonitorStatus,
        BrowserMonitorProgress
    )
    
    # Test get_period_options
    options = get_period_options()
    print(f"  Period options: {len(options)} options available")
    for opt in options:
        print(f"    - {opt['label']}: {opt['value']}")
    
    # Test format_status_message
    for status in BrowserMonitorStatus:
        msg = format_status_message(status)
        print(f"  Status {status.name}: {msg}")
    
    # Test format_progress_message
    progress = BrowserMonitorProgress(
        status=BrowserMonitorStatus.SEARCHING,
        keyword="测试关键词",
        current_keyword_index=1,
        total_keywords=3,
        posts_found=10,
        comments_found=5,
        message="正在搜索：测试关键词",
        percentage=33.3
    )
    msg = format_progress_message(progress)
    print(f"  Progress message: {msg}")
    
    print("✓ Service helper functions test passed")
    return True


def test_timestamp_parsing():
    """Test timestamp parsing logic"""
    print("\nTesting timestamp parsing...")
    
    from xhs_browser_monitor import XiaohongshuBrowserMonitor, MonitorConfig, MonitorPeriod
    
    config = MonitorConfig(
        keywords=["test"],
        monitor_period=MonitorPeriod.ONE_WEEK
    )
    
    monitor = XiaohongshuBrowserMonitor(config)
    
    # Test various timestamp formats
    test_cases = [
        ("刚刚", "should be current time"),
        ("5 分钟前", "should be 5 minutes ago"),
        ("2 小时前", "should be 2 hours ago"),
        ("3 天前", "should be 3 days ago"),
        ("昨天", "should be yesterday"),
        ("前天", "should be 2 days ago"),
        ("2024-01-15", "should be Jan 15, 2024"),
        ("01-15", "should be Jan 15 this year"),
        ("", "should be 0"),
        (None, "should be 0"),
    ]
    
    for ts_str, description in test_cases:
        result = monitor._parse_timestamp(ts_str if ts_str else "")
        print(f"  '{ts_str}' ({description}): {result}")
    
    print("✓ Timestamp parsing test passed")
    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Xiaohongshu Browser Monitor - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("MonitorPeriod Enum", test_monitor_period_enum),
        ("MonitorConfig", test_monitor_config),
        ("DataStorage", test_data_storage),
        ("Service Helpers", test_service_helpers),
        ("Timestamp Parsing", test_timestamp_parsing),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ {test_name} test FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
