#!/usr/bin/env python3
"""
Xiaohongshu Browser Monitor - Quick Start Script

快速启动小红书浏览器监控

使用方法:
    python run_xhs_monitor.py
"""

import asyncio
import sys
import os

# Add project directory to path
sys.path.insert(0, os.path.abspath('.'))

from xhs_browser_monitor import (
    XiaohongshuBrowserMonitor,
    MonitorConfig,
    MonitorPeriod,
    CHROME_PATH
)


async def main():
    """主函数"""
    print("=" * 60)
    print("小红书浏览器监控器 - 快速启动")
    print("=" * 60)
    print()
    
    # 验证 Chrome 路径
    if not os.path.exists(CHROME_PATH):
        print(f"✗ 错误：Chrome 浏览器未找到：{CHROME_PATH}")
        return
    
    print(f"✓ Chrome 浏览器路径：{CHROME_PATH}")
    print()
    
    # 配置监控参数
    print("配置监控参数...")
    config = MonitorConfig(
        keywords=["GEO 优化", "AI 搜索排名", "品牌获客"],  # 可修改为你需要的关键词
        monitor_period=MonitorPeriod.ONE_WEEK,  # 监控最近 1 周的内容
        max_posts_per_keyword=30,  # 每个关键词最多 30 篇帖子
        extract_comments=True,  # 是否提取评论
        headless=False  # 显示浏览器窗口（首次需要手动登录）
    )
    
    print(f"  关键词：{config.keywords}")
    print(f"  监控周期：{config.monitor_period.value}")
    print(f"  最大帖子数：{config.max_posts_per_keyword}")
    print(f"  提取评论：{config.extract_comments}")
    print()
    
    # 启动监控
    print("启动监控...")
    print("-" * 60)
    
    monitor = XiaohongshuBrowserMonitor(config)
    results = await monitor.run()
    
    print("-" * 60)
    print()
    print("监控完成!")
    print(f"  找到帖子数：{len(results['posts'])}")
    print(f"  找到评论数：{len(results['comments'])}")
    print(f"  结果保存至：xhs_browser_data/")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
