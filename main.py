"""
Main entry point for the Website Extractor Tools

统一启动入口，支持：
1. 通用网站内容提取器 GUI
2. 小红书监控器 GUI
3. 命令行模式
"""

import sys
import os
import argparse
from pathlib import Path


def check_dependencies():
    """检查依赖包是否安装"""
    missing = []
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    try:
        import bs4
    except ImportError:
        missing.append("beautifulsoup4")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    
    try:
        import pytesseract
    except ImportError:
        missing.append("pytesseract")
    
    try:
        import tkinter
    except ImportError:
        missing.append("tkinter")
    
    if missing:
        print("❌ 缺少必要的依赖包:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\n请运行以下命令安装:")
        print("   pip install -r requirements.txt")
        print("\n注意：OCR 功能需要单独安装 Tesseract OCR")
        print("macOS 用户：brew install tesseract")
        print("Linux 用户：sudo apt-get install tesseract-ocr")
        return False
    
    return True


def show_main_menu():
    """显示主菜单"""
    print("\n" + "=" * 60)
    print("网站内容提取工具集 v2.0")
    print("=" * 60)
    print("\n命令行模式选项:\n")
    print("  1. 通用网站内容提取器 (GUI)")
    print("  2. 小红书监控器 (GUI)")
    print("  3. 小红书账号管理 (命令行)")
    print("  4. 小红书监控器 (命令行)")
    print("  5. 退出")
    print("\n" + "=" * 60)
    print("\n提示：直接运行 'python3 main.py' 将启动统一 GUI 界面")
    print("      使用 '--menu' 参数显示此命令行菜单")
    print("=" * 60)


def launch_website_extractor_gui():
    """启动通用网站内容提取器 GUI"""
    print("\n正在启动通用网站内容提取器...")
    try:
        from gui_interface import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"❌ 启动失败：{e}")
        print("请确保 gui_interface.py 文件存在")
    except Exception as e:
        print(f"❌ 发生错误：{e}")


def launch_unified_gui():
    """启动统一的 GUI 界面 (集成所有功能)"""
    print("\n" + "=" * 60)
    print("正在启动统一 GUI 界面...")
    print("=" * 60)
    print("\n功能包括:")
    print("  • 通用网站内容提取")
    print("  • 小红书监控器 (多账号自动版)")
    print("  • 账号管理")
    print("\n如需命令行菜单，请使用：python3 main.py --menu")
    print("=" * 60)
    
    try:
        import tkinter as tk
        from gui_interface import WebsiteExtractorGUI
        
        root = tk.Tk()
        root.title("Multimodal Website Content Extractor")
        root.geometry("1200x900")
        
        # 创建应用
        app = WebsiteExtractorGUI(root)
        
        # 窗口居中
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        print("\n✅ GUI 界面已启动")
        print("   - 切换到'小红书监控器'标签页使用监控功能")
        print("   - 切换到'Extraction'标签页使用通用提取功能")
        print("\n按 Ctrl+C 可停止程序\n")
        
        # 启动主循环
        root.mainloop()
        
    except ImportError as e:
        print(f"❌ 启动失败：{e}")
        print("\n请确保 gui_interface.py 文件存在")
        print("\n或者使用命令行模式：python3 main.py --menu")
    except Exception as e:
        print(f"❌ 发生错误：{e}")
        print("\n可能的原因:")
        print("  1. tkinter 未安装")
        print("  2. 显示环境不可用 (如 SSH 连接)")
        print("\n解决方案:")
        print("  - macOS: brew install python-tk")
        print("  - Linux: sudo apt-get install python3-tk")
        print("  - 使用命令行模式：python3 main.py --menu")


def launch_xiaohongshu_monitor_gui():
    """启动小红书监控器 GUI"""
    print("\n正在启动小红书监控器...")
    try:
        from xhs_monitor_gui import XiaohongshuMonitorGUI
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
        
        print("界面已启动，请进行操作...")
        root.mainloop()
        
    except ImportError as e:
        print(f"❌ 启动失败：{e}")
        print("请确保 xhs_monitor_gui.py 文件存在")
    except Exception as e:
        print(f"❌ 发生错误：{e}")


def launch_account_manager():
    """启动账号管理命令行工具"""
    print("\n正在启动账号管理器...\n")
    try:
        from xhs_account_manager import main as account_main
        account_main()
    except ImportError as e:
        print(f"❌ 启动失败：{e}")
        print("请确保 xhs_account_manager.py 文件存在")
    except Exception as e:
        print(f"❌ 发生错误：{e}")


def launch_xiaohongshu_monitor_cli():
    """启动小红书监控器命令行模式"""
    print("\n正在启动小红书监控器 (命令行模式)...\n")
    try:
        from xhs_browser_monitor import main as monitor_main
        import asyncio
        asyncio.run(monitor_main())
    except ImportError as e:
        print(f"❌ 启动失败：{e}")
        print("请确保 xhs_browser_monitor.py 文件存在")
    except KeyboardInterrupt:
        print("\n\n用户中断，程序已退出")
    except Exception as e:
        print(f"❌ 发生错误：{e}")


def main():
    """主函数"""
    # 检查是否通过命令行参数直接启动
    parser = argparse.ArgumentParser(
        description="网站内容提取工具集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 main.py              启动统一 GUI 界面 (默认)
  python3 main.py --menu       显示命令行菜单
  python3 main.py --gui        启动通用网站提取器 GUI
  python3 main.py --xhs-gui    启动小红书监控器 GUI
  python3 main.py --xhs-cli    启动小红书监控器命令行
  python3 main.py --account    启动账号管理
        """
    )
    parser.add_argument("--gui", action="store_true", help="启动通用网站提取器 GUI")
    parser.add_argument("--xhs-gui", action="store_true", help="启动小红书监控器 GUI")
    parser.add_argument("--xhs-cli", action="store_true", help="启动小红书监控器命令行")
    parser.add_argument("--account", action="store_true", help="启动账号管理")
    parser.add_argument("--menu", action="store_true", help="显示命令行菜单")
    parser.add_argument("--no-check", action="store_true", help="跳过依赖检查")
    
    args = parser.parse_args()
    
    # 如果有命令行参数，直接启动对应功能
    if args.gui:
        if args.no_check or check_dependencies():
            launch_website_extractor_gui()
        return
    
    if args.xhs_gui:
        if args.no_check or check_dependencies():
            launch_xiaohongshu_monitor_gui()
        return
    
    if args.xhs_cli:
        launch_xiaohongshu_monitor_cli()
        return
    
    if args.account:
        launch_account_manager()
        return
    
    if args.menu:
        # 强制显示命令行菜单
        if check_dependencies():
            run_interactive_menu()
        else:
            sys.exit(1)
        return
    
    # 没有参数，默认启动统一的 GUI 界面
    if check_dependencies():
        launch_unified_gui()
    else:
        sys.exit(1)


def run_interactive_menu():
    """运行交互式菜单"""
    while True:
        show_main_menu()
        
        choice = input("\n请输入选项 (1-5): ").strip()
        
        if choice == "1":
            launch_website_extractor_gui()
        
        elif choice == "2":
            launch_xiaohongshu_monitor_gui()
        
        elif choice == "3":
            launch_account_manager()
        
        elif choice == "4":
            launch_xiaohongshu_monitor_cli()
        
        elif choice == "5":
            print("\n再见！\n")
            break
        
        else:
            print("\n❌ 无效选项，请重新输入")
            continue
        
        # 返回主菜单
        print("\n按回车键返回主菜单...")
        input()


if __name__ == "__main__":
    main()