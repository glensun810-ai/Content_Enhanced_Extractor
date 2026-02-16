#!/usr/bin/env python3
"""
小红书监控器 - GUI 启动脚本

直接运行此脚本启动图形界面
"""

import sys
import os

# 检查依赖
try:
    import tkinter
except ImportError:
    print("错误：未找到 tkinter 模块")
    print("macOS 用户请运行：brew install python-tk")
    print("Linux 用户请运行：sudo apt-get install python3-tk")
    sys.exit(1)

try:
    from xhs_monitor_gui import XiaohongshuMonitorGUI
except ImportError as e:
    print(f"错误：导入模块失败 - {e}")
    sys.exit(1)

def main():
    """主函数"""
    print("=" * 60)
    print("小红书监控器 v2.0")
    print("=" * 60)
    print("\n正在启动图形界面...")
    print("\n功能特性:")
    print("  ✅ 多账号管理和自动轮换")
    print("  ✅ AES-256 加密存储密码")
    print("  ✅ 自动登录和搜索")
    print("  ✅ 拟人化行为模拟")
    print("  ✅ 反检测保护")
    print("\n" + "=" * 60)
    
    # 创建 GUI 应用
    import tkinter as tk
    
    root = tk.Tk()
    app = XiaohongshuMonitorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 居中显示
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # 启动主循环
    print("界面已启动，请进行操作...")
    root.mainloop()
    
    print("\n程序已退出")

if __name__ == "__main__":
    main()
