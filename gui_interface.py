"""
GUI Interface for the Multimodal Website Content Extractor

统一集成界面，支持:
1. 通用网站内容提取
2. 小红书监控器 (多账号自动版)
3. 账号管理
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys
import time
import json
import queue
from pathlib import Path
from datetime import datetime
import asyncio

# Add the project directory to the path
sys.path.insert(0, os.path.abspath('.'))

# Import the required classes
from enhanced_web_text_extractor import InteractiveExtractor, DocumentManager, MultimodalDocumentManager
from multimodal_web_extractor import MultimodalWebsiteExtractor
from web_text_extractor import WebsiteTextExtractor
from js_dynamic_extractor import SpecializedJSDynamicExtractor
from xiaohongshu_scraper import XiaohongshuScraper, XiaohongshuScraperConfig
from xiaohongshu_monitoring_service import XiaohongshuMonitoringService, MonitoringConfig, MonitoringStatus
from xhs_browser_monitor_service import (
    XiaohongshuBrowserMonitorService,
    BrowserMonitorStatus,
    format_status_message,
    format_progress_message
)

# Import new XHS monitor modules
from xhs_account_manager import AccountManager, AccountStatus
from xhs_browser_monitor import XiaohongshuBrowserMonitor, MonitorConfig as XHSMonitorConfig, MonitorPeriod


class WebsiteExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multimodal Website Content Extractor")
        self.root.geometry("900x700")

        # Initialize document managers
        self.interactive_extractor = InteractiveExtractor()
        self.text_doc_manager = self.interactive_extractor.doc_manager
        self.multimodal_doc_manager = self.interactive_extractor.multimodal_doc_manager

        # Initialize monitoring control variables
        self.monitoring_active = False
        self.monitoring_thread = None

        # Initialize monitoring services
        self.monitoring_service = XiaohongshuMonitoringService()
        self.browser_monitor_service = XiaohongshuBrowserMonitorService()
        self.setup_monitoring_callbacks()
        self.setup_browser_monitor_callbacks()

        self.setup_ui()
        self.setup_cleanup_handler()
        
        # 小红书监控器相关初始化
        self.xhs_account_manager = None  # 延迟初始化
        self.xhs_monitor_running = False
        self.xhs_monitor_thread = None
        self.xhs_log_queue = None
        self.xhs_master_password_verified = False  # 主密码验证状态缓存
        self.xhs_master_password = None  # 缓存主密码

    def setup_monitoring_callbacks(self):
        """Setup callbacks for the monitoring service"""
        self.monitoring_service.on_status_change = self.on_monitoring_status_change
        self.monitoring_service.on_progress = self.on_monitoring_progress
        self.monitoring_service.on_result = self.on_monitoring_result
        self.monitoring_service.on_error = self.on_monitoring_error
        self.monitoring_service.on_complete = self.on_monitoring_complete

    def setup_browser_monitor_callbacks(self):
        """Setup callbacks for the browser monitoring service"""
        self.browser_monitor_service.on_status_change = self.on_browser_monitor_status_change
        self.browser_monitor_service.on_progress = self.on_browser_monitor_progress
        self.browser_monitor_service.on_error = self.on_browser_monitor_error
        self.browser_monitor_service.on_complete = self.on_browser_monitor_complete

    def setup_cleanup_handler(self):
        """Setup cleanup handler for when the window is closed"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handle cleanup when the application is closed"""
        # Stop any ongoing monitoring
        if self.monitoring_service.get_status() in [MonitoringStatus.RUNNING, MonitoringStatus.STOPPING]:
            self.monitoring_service.stop_monitoring()
        
        if self.browser_monitor_service.get_status() in [BrowserMonitorStatus.SEARCHING, BrowserMonitorStatus.EXTRACTING, BrowserMonitorStatus.SAVING]:
            self.browser_monitor_service.stop_monitoring()

        # Cleanup the monitoring services
        self.monitoring_service.cleanup()
        self.browser_monitor_service.cleanup()

        # Close the application
        self.root.destroy()

    def setup_ui(self):
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_extraction_tab()
        self.create_text_docs_tab()
        self.create_multimodal_docs_tab()
        self.create_xiaohongshu_monitor_tab()
        self.create_about_tab()
    
    def create_extraction_tab(self):
        # Extraction tab
        extraction_frame = ttk.Frame(self.notebook)
        self.notebook.add(extraction_frame, text="Extract Content")
        
        # URL input
        ttk.Label(extraction_frame, text="Website URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.url_entry = ttk.Entry(extraction_frame, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Max pages
        ttk.Label(extraction_frame, text="Max Pages:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_pages_var = tk.StringVar(value="10")
        max_pages_spinbox = ttk.Spinbox(extraction_frame, from_=1, to=100, textvariable=self.max_pages_var, width=10)
        max_pages_spinbox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Delay
        ttk.Label(extraction_frame, text="Delay (seconds):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.delay_var = tk.StringVar(value="1.0")
        delay_spinbox = ttk.Spinbox(extraction_frame, from_=0.1, to=10.0, increment=0.1, textvariable=self.delay_var, width=10)
        delay_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Content type selection
        self.content_type = tk.StringVar(value="multimodal")
        ttk.Radiobutton(extraction_frame, text="Text Only", variable=self.content_type, value="text").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(extraction_frame, text="Multimodal (Text + Images)", variable=self.content_type, value="multimodal").grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(extraction_frame, text="JavaScript Dynamic Content", variable=self.content_type, value="js_dynamic").grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        # Save images checkbox (for multimodal)
        self.save_images_var = tk.BooleanVar(value=True)
        self.save_images_check = ttk.Checkbutton(extraction_frame, text="Save Images", variable=self.save_images_var)
        self.save_images_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # Wait time for JS dynamic extraction
        ttk.Label(extraction_frame, text="JS Wait Time (seconds):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.js_wait_time_var = tk.StringVar(value="20")
        js_wait_time_spinbox = ttk.Spinbox(extraction_frame, from_=5, to=60, textvariable=self.js_wait_time_var, width=10)
        js_wait_time_spinbox.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Extract button
        self.extract_btn = ttk.Button(extraction_frame, text="Extract Content", command=self.start_extraction)
        self.extract_btn.grid(row=5, column=0, columnspan=3, pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(extraction_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(extraction_frame, text="Ready to extract content", foreground="blue")
        self.status_label.grid(row=7, column=0, columnspan=3, pady=5)
        
        # Output text area
        output_frame = ttk.LabelFrame(extraction_frame, text="Extraction Output")
        output_frame.grid(row=8, column=0, columnspan=3, sticky=tk.NSEW, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, width=80)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid weights
        extraction_frame.columnconfigure(1, weight=1)
        extraction_frame.rowconfigure(8, weight=1)
    
    def create_text_docs_tab(self):
        # Text documents tab
        text_docs_frame = ttk.Frame(self.notebook)
        self.notebook.add(text_docs_frame, text="Text Documents")
        
        # Document list
        list_frame = ttk.LabelFrame(text_docs_frame, text="Text Documents")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('ID', 'Title', 'Date')
        self.text_docs_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.text_docs_tree.heading(col, text=col)
            self.text_docs_tree.column(col, width=150)
        
        # Scrollbars
        text_v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.text_docs_tree.yview)
        text_h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.text_docs_tree.xview)
        self.text_docs_tree.configure(yscrollcommand=text_v_scrollbar.set, xscrollcommand=text_h_scrollbar.set)
        
        self.text_docs_tree.grid(row=0, column=0, sticky='nsew')
        text_v_scrollbar.grid(row=0, column=1, sticky='ns')
        text_h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Buttons frame
        btn_frame = ttk.Frame(text_docs_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_text_docs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="View Document", command=self.view_selected_text_doc).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Document", command=self.delete_selected_text_doc).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save to File", command=self.save_selected_text_doc).pack(side=tk.LEFT, padx=5)
        
        # Refresh initially
        self.refresh_text_docs()
    
    def create_multimodal_docs_tab(self):
        # Multimodal documents tab
        multi_docs_frame = ttk.Frame(self.notebook)
        self.notebook.add(multi_docs_frame, text="Multimodal Documents")
        
        # Document list
        list_frame = ttk.LabelFrame(multi_docs_frame, text="Multimodal Documents")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('ID', 'Title', 'Date', 'Images')
        self.multi_docs_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.multi_docs_tree.heading(col, text=col)
            self.multi_docs_tree.column(col, width=150)
        
        # Scrollbars
        multi_v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.multi_docs_tree.yview)
        multi_h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.multi_docs_tree.xview)
        self.multi_docs_tree.configure(yscrollcommand=multi_v_scrollbar.set, xscrollcommand=multi_h_scrollbar.set)
        
        self.multi_docs_tree.grid(row=0, column=0, sticky='nsew')
        multi_v_scrollbar.grid(row=0, column=1, sticky='ns')
        multi_h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Buttons frame
        btn_frame = ttk.Frame(multi_docs_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_multimodal_docs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="View Document", command=self.view_selected_multimodal_doc).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Document", command=self.delete_selected_multimodal_doc).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save to File", command=self.save_selected_multimodal_doc).pack(side=tk.LEFT, padx=5)
        
        # Refresh initially
        self.refresh_multimodal_docs()
    
    def create_xiaohongshu_monitor_tab(self):
        """创建小红书监控器标签页 - 集成多账号自动登录功能"""
        xhs_frame = ttk.Frame(self.notebook)
        self.notebook.add(xhs_frame, text="小红书监控器")
        
        # 延迟初始化账号管理器
        self.xhs_account_manager = AccountManager()
        self.xhs_log_queue = queue.Queue()
        
        # 1. 账号配置区
        account_frame = ttk.LabelFrame(xhs_frame, text="账号配置", padding="10")
        account_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 账号选择
        ttk.Label(account_frame, text="选择账号:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.xhs_account_var = tk.StringVar()
        self.xhs_account_combo = ttk.Combobox(account_frame, textvariable=self.xhs_account_var, width=40, state="readonly")
        self.xhs_account_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Button(account_frame, text="刷新", command=self.refresh_xhs_account_list).grid(row=0, column=2, padx=(10, 0), pady=5)
        ttk.Button(account_frame, text="添加账号", command=self.show_xhs_add_account_dialog).grid(row=0, column=3, padx=(5, 0), pady=5)
        ttk.Button(account_frame, text="管理账号", command=self.show_xhs_account_manager).grid(row=0, column=4, padx=(5, 0), pady=5)
        
        # 自动轮换选项
        self.xhs_auto_rotate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(account_frame, text="启用自动轮换 (推荐)", variable=self.xhs_auto_rotate_var).grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=5)
        
        # 账号状态标签
        self.xhs_account_status_label = ttk.Label(account_frame, text="", foreground="gray")
        self.xhs_account_status_label.grid(row=2, column=0, columnspan=5, sticky=tk.W, pady=2)
        
        # 2. 搜索配置区
        config_frame = ttk.LabelFrame(xhs_frame, text="搜索配置", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 关键词输入
        ttk.Label(config_frame, text="关键词 (每行一个):").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.xhs_keywords_text = scrolledtext.ScrolledText(config_frame, width=60, height=5)
        self.xhs_keywords_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        config_frame.columnconfigure(0, weight=1)
        
        # 默认关键词
        default_keywords = ["GEO 优化", "AI 搜索排名", "品牌获客"]
        self.xhs_keywords_text.insert("1.0", "\n".join(default_keywords))
        
        # 时间周期
        ttk.Label(config_frame, text="时间范围:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.xhs_period_var = tk.StringVar(value="1_week")
        period_combo = ttk.Combobox(config_frame, textvariable=self.xhs_period_var, width=20, state="readonly")
        period_combo["values"] = [
            ("1_day", "最近 1 天"),
            ("3_days", "最近 3 天"),
            ("1_week", "最近 1 周"),
            ("2_weeks", "最近 2 周"),
            ("1_month", "最近 1 个月")
        ]
        period_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 高级选项
        advanced_frame = ttk.Frame(config_frame)
        advanced_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(advanced_frame, text="每关键词最大帖子数:").grid(row=0, column=0, padx=(0, 5))
        self.xhs_max_posts_var = tk.StringVar(value="30")
        ttk.Entry(advanced_frame, textvariable=self.xhs_max_posts_var, width=10).grid(row=0, column=1, padx=(0, 20))
        
        self.xhs_extract_comments_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="提取评论", variable=self.xhs_extract_comments_var).grid(row=0, column=2, padx=(0, 20))
        
        self.xhs_headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="无头模式 (后台运行)", variable=self.xhs_headless_var).grid(row=0, column=3)
        
        # 3. 控制按钮区
        control_frame = ttk.Frame(xhs_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.xhs_start_button = ttk.Button(control_frame, text="开始监控", command=self.start_xhs_monitoring)
        self.xhs_start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.xhs_stop_button = ttk.Button(control_frame, text="停止监控", command=self.stop_xhs_monitoring, state=tk.DISABLED)
        self.xhs_stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="清空日志", command=self.clear_xhs_logs).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="打开结果目录", command=self.open_xhs_results_dir).pack(side=tk.LEFT)
        
        # 进度条
        self.xhs_progress_var = tk.DoubleVar()
        self.xhs_progress_bar = ttk.Progressbar(xhs_frame, variable=self.xhs_progress_var, maximum=100, mode="indeterminate")
        self.xhs_progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # 4. 状态显示区
        status_frame = ttk.LabelFrame(xhs_frame, text="运行状态", padding="10")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text="当前状态:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.xhs_status_label = ttk.Label(info_frame, text="就绪", foreground="green")
        self.xhs_status_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(info_frame, text="已处理关键词:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.xhs_keywords_count_label = ttk.Label(info_frame, text="0")
        self.xhs_keywords_count_label.grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(info_frame, text="已收集帖子:").grid(row=0, column=4, sticky=tk.W, padx=(20, 5))
        self.xhs_posts_count_label = ttk.Label(info_frame, text="0")
        self.xhs_posts_count_label.grid(row=0, column=5, sticky=tk.W)
        
        ttk.Label(info_frame, text="已收集评论:").grid(row=0, column=6, sticky=tk.W, padx=(20, 5))
        self.xhs_comments_count_label = ttk.Label(info_frame, text="0")
        self.xhs_comments_count_label.grid(row=0, column=7, sticky=tk.W)
        
        # 当前账号
        ttk.Label(info_frame, text="当前账号:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.xhs_current_account_label = ttk.Label(info_frame, text="-")
        self.xhs_current_account_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # 5. 日志显示区
        log_frame = ttk.LabelFrame(xhs_frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.xhs_log_text = scrolledtext.ScrolledText(log_frame, width=100, height=12, state=tk.DISABLED)
        self.xhs_log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志标签颜色
        self.xhs_log_text.tag_config("info", foreground="black")
        self.xhs_log_text.tag_config("success", foreground="green")
        self.xhs_log_text.tag_config("warning", foreground="orange")
        self.xhs_log_text.tag_config("error", foreground="red")
        
        # 启动日志更新
        self.update_xhs_logs()
        
        # 加载账号列表
        self.refresh_xhs_account_list()

    def verify_xhs_master_password_once(self, force=False):
        """
        验证主密码（带缓存，避免重复弹窗）
        
        Args:
            force: 是否强制重新验证
            
        Returns:
            bool: 验证是否成功
        """
        # 如果已经验证过且不强制重新验证，直接返回成功
        if self.xhs_master_password_verified and not force:
            return True
        
        # 检查是否有账号文件
        if not self.xhs_account_manager.accounts_file.exists():
            return True  # 首次使用，不需要验证
        
        # 检查是否已经初始化
        if self.xhs_account_manager.encryption.is_initialized():
            # 已经初始化，尝试验证
            try:
                self.xhs_account_manager._load_accounts()
                self.xhs_account_manager._master_password_set = True  # 设置标志
                self.xhs_master_password_verified = True
                return True
            except:
                pass  # 验证失败，需要重新输入
        
        # 弹出密码输入框
        from tkinter import simpledialog
        password = simpledialog.askstring(
            "主密码验证",
            "请输入主密码以解密账号信息：\n（主密码在首次添加账号时生成）",
            show="*",
            parent=self.root
        )
        
        if not password:
            return False
        
        # 设置主密码并验证
        try:
            self.xhs_account_manager.encryption.set_master_password(password)
            self.xhs_account_manager._load_accounts()
            self.xhs_account_manager._master_password_set = True  # ✅ 设置标志
            self.xhs_master_password_verified = True
            self.xhs_master_password = password
            return True
        except Exception as e:
            messagebox.showerror("错误", f"主密码验证失败：{e}")
            return False

    def create_about_tab(self):
        # About tab
        about_frame = ttk.Frame(self.notebook)
        self.notebook.add(about_frame, text="About")

        about_text = scrolledtext.ScrolledText(about_frame, wrap=tk.WORD)
        about_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        about_content = """
Multimodal Website Content Extractor

This tool extracts text, images, and preserves the structure of web pages for comprehensive AI knowledge base construction.

Features:
• Extracts text content from all pages within a domain
• Downloads and processes images from web pages
• Extracts text from images using OCR (Optical Character Recognition)
• Preserves original webpage structure and metadata
• Follows internal links up to a specified limit
• Stores and manages multiple extractions (both text-only and multimodal)
• View, save, and delete extracted documents
• Outputs to structured text documents
• Respects robots.txt and includes delays between requests
• Monitors Xiaohongshu posts with custom keywords and time periods

How to use:
1. Go to the "Extract Content" tab to extract content from websites
2. Use "Text Documents" tab to manage text-only extractions
3. Use "Multimodal Documents" tab to manage multimodal extractions
4. Use "Xiaohongshu Monitor" tab to monitor Xiaohongshu posts
5. View, save, or delete documents as needed

Note: For OCR functionality, Tesseract OCR engine needs to be installed separately.
        """

        about_text.insert(tk.END, about_content)
        about_text.config(state=tk.DISABLED)
    
    def start_extraction(self):
        """Start the extraction process in a separate thread"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a website URL")
            return
        
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Error", "URL must start with http:// or https://")
            return
        
        try:
            max_pages = int(self.max_pages_var.get())
        except ValueError:
            messagebox.showerror("Error", "Max pages must be a number")
            return
        
        try:
            delay = float(self.delay_var.get())
        except ValueError:
            messagebox.showerror("Error", "Delay must be a number")
            return
        
        # Disable UI during extraction
        self.extract_btn.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="Extracting content...", foreground="orange")
        
        # Start extraction in a separate thread
        extraction_thread = threading.Thread(
            target=self.perform_extraction,
            args=(url, max_pages, delay)
        )
        extraction_thread.daemon = True
        extraction_thread.start()
    
    def perform_extraction(self, url, max_pages, delay):
        """Perform the actual extraction"""
        try:
            if self.content_type.get() == "text":
                # Text-only extraction
                self.output_text.insert(tk.END, f"Starting text-only extraction from {url}\n")
                self.output_text.see(tk.END)

                extractor = WebsiteTextExtractor(url, max_pages, delay)
                extractor.extract_all_text()

                content = extractor.generate_document_content()

                # Create document ID
                import time
                doc_id = f"doc_{int(time.time())}"

                # Get a title for the document
                from urllib.parse import urlparse
                title = urlparse(url).netloc
                if extractor.text_content:
                    first_title = next(iter(extractor.text_content.values()))['title']
                    if first_title:
                        title = first_title[:50] + "..." if len(first_title) > 50 else first_title

                # Store the document
                self.text_doc_manager.add_document(doc_id, url, title, content)

                result_msg = f"\nText extraction complete!\nDocument ID: {doc_id}\nTitle: {title}\nPages processed: {len(extractor.text_content)}"

            elif self.content_type.get() == "js_dynamic":
                # JavaScript dynamic extraction
                self.output_text.insert(tk.END, f"Starting JavaScript dynamic extraction from {url}\n")
                self.output_text.see(tk.END)

                # Get wait time for JS dynamic extraction
                try:
                    wait_time = int(self.js_wait_time_var.get())
                except ValueError:
                    wait_time = 20  # Default value

                extractor = SpecializedJSDynamicExtractor(url, wait_time)
                extractor.extract_all_content()

                # Generate detailed report
                content = extractor.generate_detailed_report()

                # Create document ID
                import time
                doc_id = f"js_dynamic_doc_{int(time.time())}"

                # Get a title for the document
                from urllib.parse import urlparse
                title = urlparse(url).netloc
                if extractor.page_content:
                    first_title = next(iter(extractor.page_content.values()))['title']
                    if first_title:
                        title = first_title[:50] + "..." if len(first_title) > 50 else first_title

                # Store the document using the multimodal document manager
                # For JS dynamic extraction, we'll store images separately if any
                images_info = []
                if extractor.page_content:
                    first_page = next(iter(extractor.page_content.values()))
                    for img in first_page['images']:
                        # For simplicity, we won't download image data here, just store metadata
                        images_info.append({
                            'filename': img['src'].split('/')[-1] if img['src'] else 'unknown.jpg',
                            'data': b''  # Empty data since we're not downloading
                        })

                self.multimodal_doc_manager.add_document(doc_id, url, title, content, images_info)

                result_msg = f"\nJavaScript dynamic extraction complete!\nDocument ID: {doc_id}\nTitle: {title}\nPages processed: {len(extractor.page_content)}"

            else:
                # Multimodal extraction
                self.output_text.insert(tk.END, f"Starting multimodal extraction from {url}\n")
                self.output_text.see(tk.END)

                extractor = MultimodalWebsiteExtractor(url, max_pages, delay, self.save_images_var.get())
                extractor.extract_all_content()

                # Generate multimodal document
                content, images_info = extractor.generate_multimodal_document()

                # Create document ID
                import time
                doc_id = f"multi_doc_{int(time.time())}"

                # Get a title for the document
                from urllib.parse import urlparse
                title = urlparse(url).netloc
                if extractor.page_contents:
                    first_title = next(iter(extractor.page_contents.values()))['title']
                    if first_title:
                        title = first_title[:50] + "..." if len(first_title) > 50 else first_title

                # Store the document using the multimodal document manager
                self.multimodal_doc_manager.add_document(doc_id, url, title, content, images_info)

                result_msg = f"\nMultimodal extraction complete!\nDocument ID: {doc_id}\nTitle: {title}\nPages processed: {len(extractor.page_contents)}\nImages extracted: {sum(len(page_data['images']) for page_data in extractor.page_contents.values())}"

            # Update UI in the main thread
            self.root.after(0, self.extraction_complete, result_msg)

        except Exception as e:
            error_msg = f"\nExtraction failed: {str(e)}"
            self.root.after(0, self.extraction_error, error_msg)
    
    def extraction_complete(self, result_msg):
        """Called when extraction is complete"""
        self.output_text.insert(tk.END, result_msg)
        self.output_text.see(tk.END)
        
        # Re-enable UI
        self.extract_btn.config(state=tk.NORMAL)
        self.progress.stop()
        self.status_label.config(text="Extraction completed successfully", foreground="green")
        
        # Refresh document lists
        self.refresh_text_docs()
        self.refresh_multimodal_docs()
    
    def extraction_error(self, error_msg):
        """Called when extraction fails"""
        self.output_text.insert(tk.END, error_msg)
        self.output_text.see(tk.END)

        # Re-enable UI
        self.extract_btn.config(state=tk.NORMAL)
        self.progress.stop()
        self.status_label.config(text="Extraction failed", foreground="red")

    def start_xiaohongshu_monitoring(self):
        """Start the Xiaohongshu monitoring process"""
        # Get keywords
        keywords = []
        for entry in self.keyword_entries:
            keyword = entry.get().strip()
            if keyword:
                keywords.append(keyword)

        if len(keywords) < 3:
            messagebox.showerror("Error", "Please enter at least 3 keywords to monitor")
            return

        if len(keywords) > 5:
            messagebox.showerror("Error", "Maximum 5 keywords allowed")
            return

        # Get monitoring period
        period = self.monitoring_period.get()

        # Get max duration and max posts
        try:
            max_duration = int(self.monitoring_duration_var.get())
            max_posts = int(self.max_posts_var.get())
        except ValueError:
            messagebox.showerror("Error", "Duration and Max Posts must be valid numbers")
            return

        # Create monitoring configuration
        config = MonitoringConfig(
            keywords=keywords,
            monitoring_period=period,
            max_duration_minutes=max_duration,
            max_posts_per_keyword=max_posts,
            export_formats=["json"]  # Default export format
        )

        # Start monitoring via service
        success = self.monitoring_service.start_monitoring(config)

        if not success:
            messagebox.showerror("Error", "Monitoring is already running or in invalid state")
            return

        # Start progress bar
        self.xhs_progress.start()

    def perform_xiaohongshu_monitoring(self, keywords, period, max_posts_per_keyword):
        """Perform the actual Xiaohongshu monitoring"""
        try:
            # Initialize scraper
            config = XiaohongshuScraperConfig()
            scraper = XiaohongshuScraper(config)

            # Override the default max posts per keyword with the user setting
            config.max_posts_per_keyword = max_posts_per_keyword

            # Map GUI period options to scraper-compatible options
            period_mapping = {
                "1_day": "1_day",
                "3_days": "3_days",
                "1_week": "1_week",
                "custom": "1_week"  # Default to 1 week for custom
            }
            mapped_period = period_mapping.get(period, "1_week")

            # For each keyword, scrape posts
            all_results = []
            for keyword in keywords:
                # Check if monitoring is still active
                if not self.monitoring_active:
                    break

                # Check if duration limit has been reached
                elapsed_time = time.time() - self.monitoring_start_time
                if elapsed_time >= self.max_monitoring_duration:
                    self.root.after(0, self.xhs_status_label.config, text="Monitoring duration limit reached", foreground="orange")
                    break

                self.xhs_status_label.config(text=f"Monitoring keyword: {keyword}", foreground="orange")

                # Scrape posts for this keyword with the specified period
                results = scraper.scrape_keyword(keyword, export_formats=["json"], period=mapped_period)

                # Process results and filter by monitoring period if needed
                posts = results.get('posts', [])

                # Add keyword to each post for tracking
                for post in posts:
                    post['matched_keyword'] = keyword

                all_results.extend(posts)

                # Update UI periodically
                self.root.after(0, self.update_xhs_results_table, posts)

            # Update final status
            if self.monitoring_active:
                self.root.after(0, self.xiaohongshu_monitoring_complete, f"Monitoring completed! Found {len(all_results)} posts for {len(keywords)} keywords")
            else:
                self.root.after(0, self.xiaohongshu_monitoring_stopped, f"Monitoring stopped by user. Found {len(all_results)} posts for {len(keywords)} keywords")

        except Exception as e:
            error_msg = f"Monitoring failed: {str(e)}"
            self.root.after(0, self.xiaohongshu_monitoring_error, error_msg)

    def update_xhs_results_table(self, posts):
        """Update the results table with new posts"""
        for post in posts:
            # Format the date properly
            timestamp = post.get('timestamp', 0)
            if timestamp:
                # Convert from milliseconds to seconds if needed
                if timestamp > 1e10:  # If in milliseconds
                    timestamp /= 1000
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_str = "N/A"

            # Get engagement stats
            interaction_stats = post.get('interaction_stats', {})
            likes = interaction_stats.get('liked_count', 0)
            comments = interaction_stats.get('comment_count', 0)
            shares = interaction_stats.get('share_count', 0)

            # Insert into table
            self.xhs_results_tree.insert('', tk.END, values=(
                post.get('id', 'N/A'),
                post.get('title', '')[:50] + "..." if len(post.get('title', '')) > 50 else post.get('title', ''),
                post.get('author', {}).get('nickname', 'N/A'),
                date_str,
                post.get('matched_keyword', 'N/A'),
                likes,
                comments,
                shares
            ))

    def xiaohongshu_monitoring_complete(self, result_msg):
        """Called when monitoring is complete"""
        # Re-enable UI
        self.start_monitor_btn.config(state=tk.NORMAL)
        self.stop_monitor_btn.config(state=tk.DISABLED)
        self.xhs_progress.stop()
        self.xhs_status_label.config(text=result_msg, foreground="green")

    def on_monitoring_status_change(self, status):
        """Callback for monitoring status changes"""
        if status == MonitoringStatus.RUNNING:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.DISABLED),
                self.stop_monitor_btn.config(state=tk.NORMAL),
                self.xhs_status_label.config(text="Monitoring Xiaohongshu posts...", foreground="orange")
            ))
        elif status == MonitoringStatus.STOPPING:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.DISABLED),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_status_label.config(text="Stopping monitoring...", foreground="orange")
            ))
        elif status == MonitoringStatus.COMPLETED:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.NORMAL),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_progress.stop(),
                self.xhs_status_label.config(text="Monitoring completed!", foreground="green")
            ))
        elif status == MonitoringStatus.IDLE:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.NORMAL),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_progress.stop(),
                self.xhs_status_label.config(text="Ready to start monitoring", foreground="blue")
            ))
        elif status == MonitoringStatus.ERROR:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.NORMAL),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_progress.stop(),
                self.xhs_status_label.config(text="Monitoring error occurred", foreground="red")
            ))

    def on_monitoring_progress(self, progress):
        """Callback for monitoring progress updates"""
        self.root.after(0, lambda: self.xhs_status_label.config(
            text=f"Processing {progress.keyword}: {progress.posts_found} posts found ({progress.percentage:.1f}%)"
        ))

    def on_monitoring_result(self, result):
        """Callback for individual monitoring results"""
        if result.success and result.posts:
            self.root.after(0, lambda: self.update_xhs_results_table(result.posts))

    def on_monitoring_error(self, error_msg):
        """Callback for monitoring errors"""
        self.root.after(0, lambda: (
            self.start_monitor_btn.config(state=tk.NORMAL),
            self.stop_monitor_btn.config(state=tk.DISABLED),
            self.xhs_progress.stop(),
            self.xhs_status_label.config(text="Monitoring error", foreground="red"),
            messagebox.showerror("Monitoring Error", error_msg)
        ))

    def on_monitoring_complete(self, results):
        """Callback for monitoring completion"""
        total_posts = sum(r.posts_found for r in results)
        total_keywords = len(results)
        msg = f"Monitoring completed! Found {total_posts} posts for {total_keywords} keywords"
        self.root.after(0, lambda: self.xhs_status_label.config(text=msg, foreground="green"))
    
    # ========== Browser Monitor Callbacks ==========
    
    def on_browser_monitor_status_change(self, status):
        """Callback for browser monitoring status changes"""
        status_text = format_status_message(status)
        
        if status == BrowserMonitorStatus.SEARCHING:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.DISABLED),
                self.stop_monitor_btn.config(state=tk.NORMAL),
                self.xhs_status_label.config(text=f"Searching... ({status_text})", foreground="orange")
            ))
        elif status == BrowserMonitorStatus.EXTRACTING:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.DISABLED),
                self.stop_monitor_btn.config(state=tk.NORMAL),
                self.xhs_status_label.config(text=f"Extracting... ({status_text})", foreground="orange")
            ))
        elif status == BrowserMonitorStatus.SAVING:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.DISABLED),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_status_label.config(text=f"Saving... ({status_text})", foreground="orange")
            ))
        elif status == BrowserMonitorStatus.COMPLETED:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.NORMAL),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_progress.stop(),
                self.xhs_status_label.config(text="Browser monitoring completed!", foreground="green")
            ))
        elif status == BrowserMonitorStatus.IDLE:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.NORMAL),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_progress.stop(),
                self.xhs_status_label.config(text="Ready to start monitoring", foreground="blue")
            ))
        elif status == BrowserMonitorStatus.ERROR:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.NORMAL),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_progress.stop(),
                self.xhs_status_label.config(text="Browser monitoring error occurred", foreground="red")
            ))
        elif status == BrowserMonitorStatus.WAITING_LOGIN:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.DISABLED),
                self.stop_monitor_btn.config(state=tk.NORMAL),
                self.xhs_status_label.config(text="Waiting for user login... Please complete login in browser", foreground="orange")
            ))
        elif status == BrowserMonitorStatus.STOPPED:
            self.root.after(0, lambda: (
                self.start_monitor_btn.config(state=tk.NORMAL),
                self.stop_monitor_btn.config(state=tk.DISABLED),
                self.xhs_progress.stop(),
                self.xhs_status_label.config(text="Browser monitoring stopped", foreground="red")
            ))
    
    def on_browser_monitor_progress(self, progress):
        """Callback for browser monitoring progress updates"""
        progress_text = format_progress_message(progress)
        self.root.after(0, lambda: self.xhs_status_label.config(text=progress_text, foreground="orange"))
    
    def on_browser_monitor_error(self, error_msg):
        """Callback for browser monitoring errors"""
        self.root.after(0, lambda: (
            self.start_monitor_btn.config(state=tk.NORMAL),
            self.stop_monitor_btn.config(state=tk.DISABLED),
            self.xhs_progress.stop(),
            self.xhs_status_label.config(text="Browser monitoring error", foreground="red"),
            messagebox.showerror("Browser Monitoring Error", error_msg)
        ))
    
    def on_browser_monitor_complete(self, result):
        """Callback for browser monitoring completion"""
        if result.success:
            total_posts = len(result.posts)
            total_comments = len(result.comments)
            msg = f"Browser monitoring completed! Found {total_posts} posts, {total_comments} comments"
            self.root.after(0, lambda: self.xhs_status_label.config(text=msg, foreground="green"))
            
            # Store results for export
            self.browser_monitor_results = result
            
            # Update results table
            if result.posts:
                self.update_browser_monitor_results_table(result.posts)
        else:
            self.root.after(0, lambda: (
                self.xhs_status_label.config(text=f"Monitoring failed: {result.error_message}", foreground="red"),
                messagebox.showerror("Monitoring Failed", result.error_message)
            ))
    
    def update_browser_monitor_results_table(self, posts):
        """Update the results table with browser monitoring posts"""
        # Clear existing items
        for item in self.xhs_results_tree.get_children():
            self.xhs_results_tree.delete(item)
        
        for post in posts:
            # Format the date
            timestamp_str = post.get('timestamp', '')
            date_str = timestamp_str if timestamp_str else "N/A"
            
            # Get engagement stats
            likes = post.get('like_count', 0)
            comments = post.get('comment_count', 0)
            
            # Insert into table
            self.xhs_results_tree.insert('', tk.END, values=(
                post.get('id', 'N/A'),
                post.get('title', '')[:50] + "..." if len(post.get('title', '')) > 50 else post.get('title', ''),
                post.get('author_nickname', 'N/A'),
                date_str,
                post.get('keyword', 'N/A'),
                likes,
                comments
            ))
    
    def toggle_monitor_mode(self):
        """Toggle between browser and API monitoring modes"""
        if self.monitor_mode.get() == "browser":
            self.extract_comments_var.set(True)
        else:
            self.extract_comments_var.set(False)
    
    def start_xiaohongshu_monitoring(self):
        """Start the Xiaohongshu monitoring process (supports both browser and API modes)"""
        # Get keywords
        keywords = []
        for entry in self.keyword_entries:
            keyword = entry.get().strip()
            if keyword:
                keywords.append(keyword)

        if len(keywords) < 3:
            messagebox.showerror("Error", "Please enter at least 3 keywords to monitor")
            return

        if len(keywords) > 5:
            messagebox.showerror("Error", "Maximum 5 keywords allowed")
            return

        # Get monitoring period
        period = self.monitoring_period.get()
        
        # Get custom days if custom period is selected
        try:
            custom_days = int(self.custom_days_var.get())
        except ValueError:
            custom_days = 7
        
        # Get max posts
        try:
            max_posts = int(self.max_posts_var.get())
        except ValueError:
            messagebox.showerror("Error", "Max Posts must be a valid number")
            return
        
        # Get extract comments option
        extract_comments = self.extract_comments_var.get()
        
        # Check which mode is selected
        mode = self.monitor_mode.get()
        
        if mode == "browser":
            # Browser-based monitoring
            success = self.start_browser_monitoring(keywords, period, custom_days, max_posts, extract_comments)
        else:
            # API/Mock mode (existing implementation)
            success = self.start_api_monitoring(keywords, period, max_posts)
        
        if not success:
            messagebox.showerror("Error", "Monitoring is already running or in invalid state")
            return
        
        # Start progress bar
        self.xhs_progress.start()
    
    def start_browser_monitoring(self, keywords, period, custom_days, max_posts, extract_comments):
        """Start browser-based monitoring"""
        # Start monitoring via browser service
        success = self.browser_monitor_service.start_monitoring(
            keywords=keywords,
            monitor_period=period,
            custom_days=custom_days,
            max_posts_per_keyword=max_posts,
            extract_comments=extract_comments,
            headless=False  # Always show browser for user to see login status
        )
        return success
    
    def start_api_monitoring(self, keywords, period, max_posts):
        """Start API/Mock mode monitoring (existing implementation)"""
        # Get max duration
        try:
            max_duration = int(self.monitoring_duration_var.get())
        except ValueError:
            messagebox.showerror("Error", "Max Duration must be a valid number")
            return False
        
        # Create monitoring configuration
        config = MonitoringConfig(
            keywords=keywords,
            monitoring_period=period,
            max_duration_minutes=max_duration,
            max_posts_per_keyword=max_posts,
            export_formats=["json"]
        )

        # Start monitoring via service
        success = self.monitoring_service.start_monitoring(config)
        return success

    def xiaohongshu_monitoring_stopped(self, result_msg):
        """Called when monitoring is stopped by user"""
        # Re-enable UI
        self.start_monitor_btn.config(state=tk.NORMAL)
        self.stop_monitor_btn.config(state=tk.DISABLED)
        self.xhs_progress.stop()
        self.xhs_status_label.config(text=result_msg, foreground="orange")

    def xiaohongshu_monitoring_error(self, error_msg):
        """Called when monitoring fails"""
        # Re-enable UI
        self.start_monitor_btn.config(state=tk.NORMAL)
        self.stop_monitor_btn.config(state=tk.DISABLED)
        self.xhs_progress.stop()
        self.xhs_status_label.config(text="Monitoring failed", foreground="red")

        # Show error message
        messagebox.showerror("Monitoring Error", error_msg)

    def stop_xiaohongshu_monitoring(self):
        """Stop the monitoring process"""
        # Stop monitoring via service
        success = self.monitoring_service.stop_monitoring()

        if not success:
            messagebox.showwarning("Warning", "Monitoring is not currently running")
            return

    def export_xhs_results_csv(self):
        """Export results to CSV"""
        # Get all items in the treeview
        items = []
        for child in self.xhs_results_tree.get_children():
            items.append(self.xhs_results_tree.item(child)['values'])

        if not items:
            messagebox.showwarning("Warning", "No results to export")
            return

        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Results to CSV"
        )

        if file_path:
            try:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ['Post ID', 'Title', 'Author', 'Date', 'Keywords Matched', 'Likes', 'Comments', 'Shares']
                    writer = csv.writer(csvfile)

                    # Write header
                    writer.writerow(fieldnames)

                    # Write data
                    for item in items:
                        writer.writerow(item)

                messagebox.showinfo("Success", f"Results exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export results: {str(e)}")

    def export_xhs_results_excel(self):
        """Export results to Excel"""
        # Get all items in the treeview
        items = []
        for child in self.xhs_results_tree.get_children():
            items.append(self.xhs_results_tree.item(child)['values'])

        if not items:
            messagebox.showwarning("Warning", "No results to export")
            return

        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Export Results to Excel"
        )

        if file_path:
            try:
                import pandas as pd
                df = pd.DataFrame(items, columns=['Post ID', 'Title', 'Author', 'Date', 'Keywords Matched', 'Likes', 'Comments', 'Shares'])
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Success", f"Results exported to {file_path}")
            except ImportError:
                messagebox.showerror("Error", "pandas is required for Excel export. Install with: pip install pandas openpyxl")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export results: {str(e)}")

    def clear_xhs_results(self):
        """Clear the results table"""
        for item in self.xhs_results_tree.get_children():
            self.xhs_results_tree.delete(item)
        self.xhs_status_label.config(text="Results cleared", foreground="blue")
    
    def refresh_text_docs(self):
        """Refresh the text documents list"""
        # Clear existing items
        for item in self.text_docs_tree.get_children():
            self.text_docs_tree.delete(item)
        
        # Load documents
        docs = self.text_doc_manager.list_documents()
        for doc in docs:
            self.text_docs_tree.insert('', tk.END, values=(
                doc['id'],
                doc['title'][:47] + "..." if len(doc['title']) > 50 else doc['title'],  # Truncate long titles
                doc['timestamp'][:19]  # Show only date and time
            ))
    
    def refresh_multimodal_docs(self):
        """Refresh the multimodal documents list"""
        # Clear existing items
        for item in self.multi_docs_tree.get_children():
            self.multi_docs_tree.delete(item)
        
        # Load documents
        docs = self.multimodal_doc_manager.list_documents()
        for doc in docs:
            self.multi_docs_tree.insert('', tk.END, values=(
                doc['id'],
                doc['title'][:47] + "..." if len(doc['title']) > 50 else doc['title'],  # Truncate long titles
                doc['timestamp'][:19],  # Show only date and time
                doc['image_count']
            ))
    
    def view_selected_text_doc(self):
        """View the selected text document"""
        selected_item = self.text_docs_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a document to view")
            return
        
        item_values = self.text_docs_tree.item(selected_item)['values']
        doc_id = item_values[0]
        
        doc = self.text_doc_manager.get_document(doc_id)
        if not doc:
            messagebox.showerror("Error", f"Could not find document with ID: {doc_id}")
            return
        
        # Create a new window to display the document
        self.show_document_window(doc, f"Text Document: {doc_id}")
    
    def view_selected_multimodal_doc(self):
        """View the selected multimodal document"""
        selected_item = self.multi_docs_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a document to view")
            return
        
        item_values = self.multi_docs_tree.item(selected_item)['values']
        doc_id = item_values[0]
        
        doc = self.multimodal_doc_manager.get_document(doc_id)
        if not doc:
            messagebox.showerror("Error", f"Could not find document with ID: {doc_id}")
            return
        
        # Create a new window to display the document
        self.show_document_window(doc, f"Multimodal Document: {doc_id}")
    
    def show_document_window(self, doc, title):
        """Show document in a new window"""
        doc_window = tk.Toplevel(self.root)
        doc_window.title(title)
        doc_window.geometry("800x600")
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(doc_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Insert document content
        content = f"URL: {doc['url']}\n"
        content += f"Title: {doc['title']}\n"
        content += f"Timestamp: {doc['timestamp']}\n"
        if 'image_count' in doc:
            content += f"Images: {doc['image_count']}\n"
            if 'image_files' in doc and doc['image_files']:
                content += f"Image Files: {', '.join(doc['image_files'][:5])}{'...' if len(doc['image_files']) > 5 else ''}\n"
        content += "\n" + "="*80 + "\n\n"
        content += doc['content']
        
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)
    
    def delete_selected_text_doc(self):
        """Delete the selected text document"""
        selected_item = self.text_docs_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a document to delete")
            return
        
        item_values = self.text_docs_tree.item(selected_item)['values']
        doc_id = item_values[0]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete document {doc_id}?"):
            if self.text_doc_manager.delete_document(doc_id):
                messagebox.showinfo("Success", f"Document {doc_id} deleted successfully")
                self.refresh_text_docs()
            else:
                messagebox.showerror("Error", f"Failed to delete document {doc_id}")
    
    def delete_selected_multimodal_doc(self):
        """Delete the selected multimodal document"""
        selected_item = self.multi_docs_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a document to delete")
            return
        
        item_values = self.multi_docs_tree.item(selected_item)['values']
        doc_id = item_values[0]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete document {doc_id}?"):
            if self.multimodal_doc_manager.delete_document(doc_id):
                messagebox.showinfo("Success", f"Document {doc_id} deleted successfully")
                self.refresh_multimodal_docs()
            else:
                messagebox.showerror("Error", f"Failed to delete document {doc_id}")
    
    def save_selected_text_doc(self):
        """Save the selected text document to a file"""
        selected_item = self.text_docs_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a document to save")
            return
        
        item_values = self.text_docs_tree.item(selected_item)['values']
        doc_id = item_values[0]
        
        doc = self.text_doc_manager.get_document(doc_id)
        if not doc:
            messagebox.showerror("Error", f"Could not find document with ID: {doc_id}")
            return
        
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Text Document"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(doc['content'])
                messagebox.showinfo("Success", f"Document saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save document: {str(e)}")
    
    def save_selected_multimodal_doc(self):
        """Save the selected multimodal document to a file"""
        selected_item = self.multi_docs_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a document to save")
            return

        item_values = self.multi_docs_tree.item(selected_item)['values']
        doc_id = item_values[0]

        doc = self.multimodal_doc_manager.get_document(doc_id)
        if not doc:
            messagebox.showerror("Error", f"Could not find document with ID: {doc_id}")
            return

        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Multimodal Document"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(doc['content'])
                messagebox.showinfo("Success", f"Document saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save document: {str(e)}")

    # ==================== 小红书监控器新方法 ====================
    
    def refresh_xhs_account_list(self):
        """刷新账号列表"""
        # 确保账号管理器已初始化
        if self.xhs_account_manager is None:
            self.xhs_account_manager = AccountManager()
            self.xhs_log_queue = queue.Queue()
        
        try:
            # 使用优化后的验证方法
            if not self.verify_xhs_master_password_once():
                self.xhs_account_combo["values"] = ["主密码验证失败"]
                self.xhs_account_var.set("主密码验证失败")
                return
            
            if not self.xhs_account_manager.accounts_file.exists():
                self.xhs_account_combo["values"] = ["暂无账号，请点击添加"]
                self.xhs_account_var.set("暂无账号，请点击添加")
                self.xhs_account_status_label.config(text="未检测到账号配置", foreground="gray")
                return
            
            # 获取账号列表
            accounts = self.xhs_account_manager.list_accounts()
            if not accounts:
                self.xhs_account_combo["values"] = ["暂无账号，请点击添加"]
                self.xhs_account_var.set("暂无账号，请点击添加")
            else:
                values = []
                for acc in accounts:
                    status_icon = {
                        "active": "✅",
                        "suspicious": "⚠️",
                        "limited": "🚫",
                        "banned": "❌",
                        "unknown": "❓"
                    }.get(acc["status"], "")
                    values.append(f"{acc['account_id']} - {acc['username']} {status_icon}")
                
                self.xhs_account_combo["values"] = values + ["自动轮换"]
                if self.xhs_auto_rotate_var.get():
                    self.xhs_account_var.set("自动轮换")
                else:
                    self.xhs_account_var.set(values[0] if values else "")
            
            # 更新状态
            stats = self.xhs_account_manager.get_account_statistics()
            status_text = f"总账号：{stats['total']}, 可用：{stats['total'] - stats['by_status'].get('banned', 0) - stats['by_status'].get('limited', 0)}, 冷却中：{stats.get('in_cooldown', 0)}"
            self.xhs_account_status_label.config(text=status_text, foreground="blue")
            
        except Exception as e:
            self.xhs_log(f"刷新账号列表失败：{e}", "error")
    
    def show_xhs_add_account_dialog(self):
        """显示添加账号对话框"""
        # 确保账号管理器已初始化
        if self.xhs_account_manager is None:
            self.xhs_account_manager = AccountManager()
            self.xhs_log_queue = queue.Queue()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("添加小红书账号")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 标题
        title_frame = ttk.Frame(dialog)
        title_frame.pack(fill=tk.X, pady=10)
        ttk.Label(title_frame, text="添加小红书账号", font=("Arial", 14, "bold")).pack()
        ttk.Label(title_frame, text="账号信息将使用 AES-256 加密存储", font=("Arial", 9), foreground="gray").pack()
        
        # 表单区域
        form_frame = ttk.LabelFrame(dialog, text="账号信息", padding="15")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        form_frame.columnconfigure(1, weight=1)
        
        # 账号
        ttk.Label(form_frame, text="账号:").grid(row=0, column=0, sticky=tk.W, pady=8)
        username_entry = ttk.Entry(form_frame, width=40)
        username_entry.grid(row=0, column=1, sticky=tk.EW, pady=8, padx=(10, 0))
        ttk.Label(form_frame, text="(手机号或邮箱)", foreground="gray", font=("Arial", 8)).grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        
        # 密码
        ttk.Label(form_frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=8)
        password_entry = ttk.Entry(form_frame, width=40, show="•")
        password_entry.grid(row=1, column=1, sticky=tk.EW, pady=8, padx=(10, 0))
        
        # 手机号
        ttk.Label(form_frame, text="手机号:").grid(row=2, column=0, sticky=tk.W, pady=8)
        phone_entry = ttk.Entry(form_frame, width=40)
        phone_entry.grid(row=2, column=1, sticky=tk.EW, pady=8, padx=(10, 0))
        ttk.Label(form_frame, text="(可选，用于接收验证码)", foreground="gray", font=("Arial", 8)).grid(row=2, column=2, sticky=tk.W, padx=(5, 0))
        
        # 备注
        ttk.Label(form_frame, text="备注:").grid(row=3, column=0, sticky=tk.W, pady=8)
        notes_entry = ttk.Entry(form_frame, width=40)
        notes_entry.grid(row=3, column=1, sticky=tk.EW, pady=8, padx=(10, 0))
        
        # 按钮区域
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=15)
        
        def on_save():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            phone = phone_entry.get().strip()
            notes = notes_entry.get().strip()
            
            if not username or not password:
                messagebox.showwarning("⚠️ 警告", "账号和密码不能为空")
                return
            
            try:
                # 检查是否是首次添加
                is_first_account = not self.xhs_account_manager.accounts_file.exists()
                
                if is_first_account:
                    # 首次添加，生成随机主密码
                    import secrets
                    master_password = secrets.token_urlsafe(16)
                    self.xhs_account_manager.encryption.set_master_password(master_password)
                    self.xhs_account_manager._master_password_set = True  # ✅ 设置标志
                    
                    # 显示主密码
                    msg = (f"✅ 主密码已生成\n\n"
                          f"主密码：{master_password}\n\n"
                          f"⚠️ 重要提示：\n"
                          f"1. 请复制并妥善保管此密码\n"
                          f"2. 主密码丢失后将无法恢复账号密码\n"
                          f"3. 建议存储在密码管理器或安全的地方")
                    
                    messagebox.showinfo("🔐 主密码设置", msg, parent=dialog)
                    
                    # 设置验证状态
                    self.xhs_master_password_verified = True
                else:
                    # 非首次添加，使用优化后的验证
                    if not self.verify_xhs_master_password_once():
                        messagebox.showerror("❌ 错误", "主密码验证失败，无法添加账号")
                        return
                
                # 添加账号
                self.xhs_account_manager.add_account(username, password, phone, notes)
                
                # 成功提示
                success_msg = f"✅ 账号已添加成功！\n\n账号：{username}"
                if phone:
                    success_msg += f"\n手机号：{phone}"
                if notes:
                    success_msg += f"\n备注：{notes}"
                
                messagebox.showinfo("✅ 成功", success_msg, parent=dialog)
                
                # 刷新列表并关闭对话框
                self.refresh_xhs_account_list()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("❌ 错误", f"添加账号失败：{e}", parent=dialog)
        
        # 保存按钮（突出显示）
        save_btn = ttk.Button(btn_frame, text="💾 保存账号", command=on_save)
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 取消按钮
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # 帮助提示
        help_frame = ttk.Frame(dialog)
        help_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        ttk.Label(help_frame, 
                 text="💡 提示：首次添加账号时会生成主密码，后续添加账号需要验证主密码",
                 font=("Arial", 9),
                 foreground="gray").pack()
    
    def show_xhs_account_manager(self):
        """显示账号管理器对话框"""
        # 确保账号管理器已初始化
        if self.xhs_account_manager is None:
            self.xhs_account_manager = AccountManager()
            self.xhs_log_queue = queue.Queue()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("账号管理")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 标题
        ttk.Label(dialog, text="小红书账号管理", font=("Arial", 14, "bold")).pack(pady=10)
        
        # 账号列表框架
        list_frame = ttk.LabelFrame(dialog, text="账号列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建树形列表
        columns = ('账号 ID', '用户名', '状态', '使用次数', '最后使用', '备注')
        self.account_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 设置列标题
        for col in columns:
            self.account_tree.heading(col, text=col)
            self.account_tree.column(col, width=100)
        
        self.account_tree.column('用户名', width=150)
        self.account_tree.column('备注', width=150)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.account_tree.yview)
        self.account_tree.configure(yscrollcommand=scrollbar.set)
        
        self.account_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="添加账号", command=lambda: self.add_account_from_manager(dialog)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="刷新列表", command=lambda: self.load_accounts_to_tree()).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除账号", command=lambda: self.delete_selected_account(dialog)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重置状态", command=lambda: self.reset_selected_account(dialog)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 状态标签
        self.account_manager_status = ttk.Label(dialog, text="", foreground="gray")
        self.account_manager_status.pack(pady=(0, 10))
        
        # 加载账号列表
        try:
            self.load_accounts_to_tree()
        except Exception as e:
            messagebox.showerror("错误", f"加载账号列表失败：{e}")
    
    def load_accounts_to_tree(self):
        """加载账号列表到树形控件"""
        # 清空现有项
        for item in self.account_tree.get_children():
            self.account_tree.delete(item)
        
        try:
            # 使用优化后的验证方法
            if not self.verify_xhs_master_password_once():
                self.account_manager_status.config(text="主密码验证失败", foreground="red")
                return
            
            # 获取账号列表
            accounts = self.xhs_account_manager.list_accounts()
            
            if not accounts:
                self.account_manager_status.config(text="暂无账号", foreground="orange")
                return
            
            # 添加到树形列表
            for acc in accounts:
                status_icon = {
                    "active": "✅",
                    "suspicious": "⚠️",
                    "limited": "🚫",
                    "banned": "❌",
                    "unknown": "❓"
                }.get(acc["status"], "")
                
                last_used = acc.get("last_used_at", "从未")[:19] if acc.get("last_used_at") else "从未"
                
                self.account_tree.insert("", tk.END, values=(
                    acc["account_id"],
                    acc["username"],
                    f"{status_icon} {acc['status']}",
                    acc.get("total_searches", 0),
                    last_used,
                    acc.get("notes", "")
                ))
            
            # 更新状态
            stats = self.xhs_account_manager.get_account_statistics()
            status_text = f"总账号：{stats['total']}, 可用：{stats['total'] - stats['by_status'].get('banned', 0) - stats['by_status'].get('limited', 0)}, 冷却中：{stats.get('in_cooldown', 0)}"
            self.account_manager_status.config(text=status_text, foreground="blue")
            
        except Exception as e:
            self.account_manager_status.config(text=f"加载失败：{e}", foreground="red")
    
    def add_account_from_manager(self, dialog):
        """从管理器添加账号"""
        dialog.destroy()
        self.show_xhs_add_account_dialog()
        # 重新打开管理器刷新列表
        self.root.after(500, self.show_xhs_account_manager)
    
    def delete_selected_account(self, dialog):
        """删除选中的账号"""
        selected = self.account_tree.selection()
        if not selected:
            messagebox.showwarning("⚠️ 警告", "请先选择要删除的账号")
            return
        
        item = self.account_tree.item(selected[0])
        account_id = item['values'][0]
        username = item['values'][1]
        
        if messagebox.askyesno("❓ 确认删除", 
                              f"确定要删除账号 {username} 吗？\n\n此操作不可恢复！",
                              parent=dialog):
            try:
                # 使用优化后的验证方法
                if not self.verify_xhs_master_password_once():
                    messagebox.showerror("❌ 错误", "主密码验证失败")
                    return
                
                # 删除账号
                self.xhs_account_manager.remove_account(account_id)
                messagebox.showinfo("✅ 成功", f"账号 {username} 已删除", parent=dialog)
                
                # 刷新列表
                self.load_accounts_to_tree()
                
            except Exception as e:
                messagebox.showerror("❌ 错误", f"删除失败：{e}", parent=dialog)
    
    def reset_selected_account(self, dialog):
        """重置选中账号的状态"""
        selected = self.account_tree.selection()
        if not selected:
            messagebox.showwarning("⚠️ 警告", "请先选择要重置的账号")
            return
        
        item = self.account_tree.item(selected[0])
        account_id = item['values'][0]
        username = item['values'][1]
        
        if messagebox.askyesno("❓ 确认重置", 
                              f"确定要重置账号 {username} 的状态吗？\n\n这将清除该账号的失败记录和冷却状态。",
                              parent=dialog):
            try:
                # 使用优化后的验证方法
                if not self.verify_xhs_master_password_once():
                    messagebox.showerror("❌ 错误", "主密码验证失败")
                    return
                
                # 获取账号并重置
                account = self.xhs_account_manager.get_account(account_id)
                if account:
                    account.consecutive_failures = 0
                    account.last_error = ""
                    account.status = AccountStatus.ACTIVE.value
                    self.xhs_account_manager._save_accounts()
                    
                    messagebox.showinfo("✅ 成功", f"账号 {username} 状态已重置", parent=dialog)
                    
                    # 刷新列表
                    self.load_accounts_to_tree()
                
            except Exception as e:
                messagebox.showerror("❌ 错误", f"重置失败：{e}", parent=dialog)
    
    def xhs_log(self, message: str, level: str = "info"):
        """添加日志"""
        self.xhs_log_queue.put((message, level))
    
    def update_xhs_logs(self):
        """更新日志显示"""
        try:
            while True:
                message, level = self.xhs_log_queue.get_nowait()
                self.xhs_log_text.config(state=tk.NORMAL)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.xhs_log_text.insert(tk.END, f"[{timestamp}] {message}\n", level)
                self.xhs_log_text.see(tk.END)
                self.xhs_log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_xhs_logs)
    
    def clear_xhs_logs(self):
        """清空日志"""
        self.xhs_log_text.config(state=tk.NORMAL)
        self.xhs_log_text.delete("1.0", tk.END)
        self.xhs_log_text.config(state=tk.DISABLED)
    
    def open_xhs_results_dir(self):
        """打开结果目录"""
        results_dir = Path("xhs_browser_data")
        if results_dir.exists():
            os.system(f"open {results_dir}")
        else:
            messagebox.showinfo("提示", "结果目录不存在，请先运行监控任务")
    
    def start_xhs_monitoring(self):
        """开始监控"""
        # 确保账号管理器已初始化
        if self.xhs_account_manager is None:
            self.xhs_account_manager = AccountManager()
            self.xhs_log_queue = queue.Queue()
        
        if self.xhs_monitor_running:
            messagebox.showwarning("警告", "监控任务已在运行中")
            return

        # 获取配置
        try:
            keywords_text = self.xhs_keywords_text.get("1.0", tk.END).strip()
            keywords = [k.strip() for k in keywords_text.split("\n") if k.strip()]

            if not keywords:
                messagebox.showwarning("警告", "请至少输入一个关键词")
                return

            max_posts = int(self.xhs_max_posts_var.get())
            if max_posts <= 0:
                raise ValueError("帖子数必须大于 0")

            period_map = {
                "1_day": MonitorPeriod.ONE_DAY,
                "3_days": MonitorPeriod.THREE_DAYS,
                "1_week": MonitorPeriod.ONE_WEEK,
                "2_weeks": MonitorPeriod.TWO_WEEKS,
                "1_month": MonitorPeriod.ONE_MONTH
            }
            period = period_map.get(self.xhs_period_var.get(), MonitorPeriod.ONE_WEEK)

        except ValueError as e:
            messagebox.showerror("错误", f"配置错误：{e}")
            return

        # 检查账号
        if not self.xhs_account_manager.accounts_file.exists():
            if not messagebox.askyesno("确认", "未检测到账号配置，是否现在添加？"):
                return
            self.show_xhs_add_account_dialog()
            return
        
        # 创建配置
        config = XHSMonitorConfig(
            keywords=keywords,
            monitor_period=period,
            max_posts_per_keyword=max_posts,
            extract_comments=self.xhs_extract_comments_var.get(),
            headless=self.xhs_headless_var.get()
        )
        
        # 启动任务
        self.xhs_monitor_running = True
        self.xhs_start_button.config(state=tk.DISABLED)
        self.xhs_stop_button.config(state=tk.NORMAL)
        self.xhs_progress_bar.start()
        self.xhs_status_label.config(text="运行中", foreground="blue")
        
        self.xhs_log(f"开始监控，关键词：{', '.join(keywords)}", "info")
        self.xhs_log(f"时间范围：{self.xhs_period_var.get()}, 最大帖子数：{max_posts}", "info")
        
        # 在后台线程运行
        self.xhs_monitor_thread = threading.Thread(target=self.run_xhs_monitoring, args=(config,), daemon=True)
        self.xhs_monitor_thread.start()
    
    def run_xhs_monitoring(self, config):
        """运行监控任务 (后台线程)"""
        try:
            # 验证主密码
            if not self.xhs_account_manager.encryption.is_initialized():
                if self.xhs_account_manager.encryption.salt_file.exists():
                    # 需要在主线程验证密码
                    self.root.after(0, lambda: self.verify_xhs_master_password(config))
                    return
            
            # 创建监控器
            monitor = XiaohongshuBrowserMonitor(
                config,
                account_manager=self.xhs_account_manager
            )
            
            # 运行监控
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                results = loop.run_until_complete(monitor.run())
                # 使用默认参数捕获 results 值
                self.root.after(0, lambda res=results: self.on_xhs_monitoring_complete(res))
            finally:
                loop.close()

        except Exception as e:
            # 使用默认参数捕获 e 值
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.on_xhs_monitoring_error(msg))
    
    def verify_xhs_master_password(self, config):
        """为任务验证主密码"""
        password = self.xhs_account_manager.setup_master_password()
        if not password:
            self.xhs_log("主密码验证失败，任务取消", "error")
            self.stop_xhs_monitoring()
            return
        
        # 重新运行监控
        self.xhs_monitor_thread = threading.Thread(target=self.run_xhs_monitoring, args=(config,), daemon=True)
        self.xhs_monitor_thread.start()
    
    def on_xhs_monitoring_complete(self, results):
        """监控完成回调"""
        self.xhs_monitor_running = False
        self.xhs_start_button.config(state=tk.NORMAL)
        self.xhs_stop_button.config(state=tk.DISABLED)
        self.xhs_progress_bar.stop()
        self.xhs_status_label.config(text="已完成", foreground="green")
        
        # 更新统计
        stats = results.get("stats", {})
        self.xhs_keywords_count_label.config(text=str(stats.get("keywords_processed", 0)))
        self.xhs_posts_count_label.config(text=str(stats.get("total_posts", 0)))
        self.xhs_comments_count_label.config(text=str(stats.get("total_comments", 0)))
        
        self.xhs_log(f"监控完成，收集帖子：{stats.get('total_posts', 0)}, 评论：{stats.get('total_comments', 0)}", "success")
        
        messagebox.showinfo("完成", f"监控任务已完成!\n\n帖子：{stats.get('total_posts', 0)}\n评论：{stats.get('total_comments', 0)}\n\n结果已保存。")
    
    def on_xhs_monitoring_error(self, error):
        """监控错误回调"""
        self.xhs_monitor_running = False
        self.xhs_start_button.config(state=tk.NORMAL)
        self.xhs_stop_button.config(state=tk.DISABLED)
        self.xhs_progress_bar.stop()
        self.xhs_status_label.config(text="错误", foreground="red")
        
        self.xhs_log(f"监控任务出错：{error}", "error")
        messagebox.showerror("错误", f"监控任务失败:\n{error}")
    
    def stop_xhs_monitoring(self):
        """停止监控"""
        if not self.xhs_monitor_running:
            return
        
        self.xhs_monitor_running = False
        self.xhs_start_button.config(state=tk.NORMAL)
        self.xhs_stop_button.config(state=tk.DISABLED)
        self.xhs_progress_bar.stop()
        self.xhs_status_label.config(text="已停止", foreground="orange")
        
        self.xhs_log("监控任务已停止", "warning")


def main():
    root = tk.Tk()
    app = WebsiteExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()