"""
小红书监控器 GUI 界面

集成账号管理、自动登录和关键词搜索功能
用户可以直接在界面上输入账号密码和搜索配置，自动执行内容搜集
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
import queue

# 导入账号管理模块
from xhs_account_manager import AccountManager, AccountStatus
from xhs_browser_monitor import XiaohongshuBrowserMonitor, MonitorConfig, MonitorPeriod


class XiaohongshuMonitorGUI:
    """小红书监控器 GUI 界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("小红书监控器 - 多账号自动版")
        self.root.geometry("1100x800")
        
        # 初始化账号管理器
        self.account_manager = AccountManager()
        
        # 任务控制
        self.task_running = False
        self.task_thread = None
        self.log_queue = queue.Queue()
        
        # 当前配置
        self.current_config = None
        
        # 创建界面
        self.create_menu()
        self.create_widgets()
        
        # 启动日志更新
        self.update_logs()
        
        # 加载账号列表
        self.refresh_account_list()
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出配置", command=self.export_config)
        file_menu.add_command(label="导入配置", command=self.import_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        
        # 账号菜单
        account_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="账号管理", menu=account_menu)
        account_menu.add_command(label="添加账号", command=self.show_add_account_dialog)
        account_menu.add_command(label="管理账号", command=self.show_account_manager)
        account_menu.add_separator()
        account_menu.add_command(label="清除登录状态", command=self.clear_login_states)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_widgets(self):
        """创建主界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(W, E, N, S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 1. 账号配置区
        self.create_account_section(main_frame)
        
        # 2. 搜索配置区
        self.create_search_config_section(main_frame)
        
        # 3. 控制按钮区
        self.create_control_section(main_frame)
        
        # 4. 状态显示区
        self.create_status_section(main_frame)
        
        # 5. 日志显示区
        self.create_log_section(main_frame)
    
    def create_account_section(self, parent):
        """创建账号配置区"""
        account_frame = ttk.LabelFrame(parent, text="账号配置", padding="10")
        account_frame.grid(row=0, column=0, sticky=(W, E), pady=(0, 10))
        parent.columnconfigure(0, weight=1)
        
        # 账号选择
        ttk.Label(account_frame, text="选择账号:").grid(row=0, column=0, sticky=W, pady=5)
        
        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(account_frame, textvariable=self.account_var, width=40, state="readonly")
        self.account_combo.grid(row=0, column=1, sticky=W, padx=(10, 0), pady=5)
        
        ttk.Button(account_frame, text="刷新", command=self.refresh_account_list).grid(row=0, column=2, padx=(10, 0), pady=5)
        ttk.Button(account_frame, text="添加账号", command=self.show_add_account_dialog).grid(row=0, column=3, padx=(5, 0), pady=5)
        
        # 自动轮换选项
        self.auto_rotate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(account_frame, text="启用自动轮换 (推荐)", variable=self.auto_rotate_var).grid(row=1, column=0, columnspan=4, sticky=W, pady=5)
        
        # 账号状态标签
        self.account_status_label = ttk.Label(account_frame, text="", foreground="gray")
        self.account_status_label.grid(row=2, column=0, columnspan=4, sticky=W, pady=2)
    
    def create_search_config_section(self, parent):
        """创建搜索配置区"""
        config_frame = ttk.LabelFrame(parent, text="搜索配置", padding="10")
        config_frame.grid(row=1, column=0, sticky=(W, E), pady=(0, 10))
        parent.columnconfigure(0, weight=1)
        
        # 关键词输入
        ttk.Label(config_frame, text="关键词 (每行一个):").grid(row=0, column=0, sticky=W, pady=5)
        
        self.keywords_text = scrolledtext.ScrolledText(config_frame, width=60, height=5)
        self.keywords_text.grid(row=1, column=0, columnspan=2, sticky=(W, E), pady=5)
        config_frame.columnconfigure(0, weight=1)
        
        # 默认关键词
        default_keywords = ["GEO 优化", "AI 搜索排名", "品牌获客"]
        self.keywords_text.insert("1.0", "\n".join(default_keywords))
        
        # 时间周期
        ttk.Label(config_frame, text="时间范围:").grid(row=2, column=0, sticky=W, pady=5)
        
        self.period_var = tk.StringVar(value="1_week")
        period_combo = ttk.Combobox(config_frame, textvariable=self.period_var, width=20, state="readonly")
        period_combo["values"] = [
            ("1_day", "最近 1 天"),
            ("3_days", "最近 3 天"),
            ("1_week", "最近 1 周"),
            ("2_weeks", "最近 2 周"),
            ("1_month", "最近 1 个月")
        ]
        period_combo.grid(row=2, column=1, sticky=W, padx=(10, 0), pady=5)
        
        # 高级选项
        advanced_frame = ttk.Frame(config_frame)
        advanced_frame.grid(row=3, column=0, columnspan=2, sticky=W, pady=(10, 0))
        
        ttk.Label(advanced_frame, text="每关键词最大帖子数:").grid(row=0, column=0, padx=(0, 5))
        self.max_posts_var = tk.StringVar(value="30")
        ttk.Entry(advanced_frame, textvariable=self.max_posts_var, width=10).grid(row=0, column=1, padx=(0, 20))
        
        self.extract_comments_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="提取评论", variable=self.extract_comments_var).grid(row=0, column=2, padx=(0, 20))
        
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="无头模式 (后台运行)", variable=self.headless_var).grid(row=0, column=3)
    
    def create_control_section(self, parent):
        """创建控制按钮区"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, sticky=(W, E), pady=(0, 10))
        parent.columnconfigure(0, weight=1)
        
        self.start_button = ttk.Button(control_frame, text="开始监控", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="停止监控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="清空日志", command=self.clear_logs).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="打开结果目录", command=self.open_results_dir).pack(side=tk.LEFT)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100, mode="indeterminate")
        self.progress_bar.grid(row=3, column=0, sticky=(W, E), pady=(0, 10))
        parent.columnconfigure(0, weight=1)
    
    def create_status_section(self, parent):
        """创建状态显示区"""
        status_frame = ttk.LabelFrame(parent, text="运行状态", padding="10")
        status_frame.grid(row=4, column=0, sticky=(W, E, N, S), pady=(0, 10))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)
        
        # 状态信息网格
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text="当前状态:").grid(row=0, column=0, sticky=W, padx=(0, 5))
        self.status_label = ttk.Label(info_frame, text="就绪", foreground="green")
        self.status_label.grid(row=0, column=1, sticky=W)
        
        ttk.Label(info_frame, text="已处理关键词:").grid(row=0, column=2, sticky=W, padx=(20, 5))
        self.keywords_count_label = ttk.Label(info_frame, text="0")
        self.keywords_count_label.grid(row=0, column=3, sticky=W)
        
        ttk.Label(info_frame, text="已收集帖子:").grid(row=0, column=4, sticky=W, padx=(20, 5))
        self.posts_count_label = ttk.Label(info_frame, text="0")
        self.posts_count_label.grid(row=0, column=5, sticky=W)
        
        ttk.Label(info_frame, text="已收集评论:").grid(row=0, column=6, sticky=W, padx=(20, 5))
        self.comments_count_label = ttk.Label(info_frame, text="0")
        self.comments_count_label.grid(row=0, column=7, sticky=W)
        
        # 当前账号
        ttk.Label(info_frame, text="当前账号:").grid(row=1, column=0, sticky=W, padx=(0, 5), pady=(5, 0))
        self.current_account_label = ttk.Label(info_frame, text="-")
        self.current_account_label.grid(row=1, column=1, sticky=W, pady=(5, 0))
    
    def create_log_section(self, parent):
        """创建日志显示区"""
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="10")
        log_frame.grid(row=5, column=0, sticky=(W, E, N, S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(5, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=100, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志标签颜色
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")
    
    def log(self, message: str, level: str = "info"):
        """添加日志"""
        self.log_queue.put((message, level))
    
    def update_logs(self):
        """更新日志显示"""
        try:
            while True:
                message, level = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", level)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_logs)
    
    def refresh_account_list(self):
        """刷新账号列表"""
        try:
            if not self.account_manager.accounts_file.exists():
                self.account_combo["values"] = ["暂无账号，请点击添加"]
                self.account_var.set("暂无账号，请点击添加")
                self.account_status_label.config(text="未检测到账号配置", foreground="gray")
                return
            
            # 验证主密码
            password = self.account_manager.setup_master_password()
            if not password:
                messagebox.showerror("错误", "主密码验证失败")
                return
            
            # 获取账号列表
            accounts = self.account_manager.list_accounts()
            if not accounts:
                self.account_combo["values"] = ["暂无账号，请点击添加"]
                self.account_var.set("暂无账号，请点击添加")
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
                
                self.account_combo["values"] = values + ["自动轮换"]
                if self.auto_rotate_var.get():
                    self.account_var.set("自动轮换")
                else:
                    self.account_var.set(values[0] if values else "")
            
            # 更新状态
            stats = self.account_manager.get_account_statistics()
            status_text = f"总账号：{stats['total']}, 可用：{stats['total'] - stats['by_status'].get('banned', 0) - stats['by_status'].get('limited', 0)}, 冷却中：{stats.get('in_cooldown', 0)}"
            self.account_status_label.config(text=status_text, foreground="blue")
            
        except Exception as e:
            self.log(f"刷新账号列表失败：{e}", "error")
    
    def show_add_account_dialog(self):
        """显示添加账号对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加小红书账号")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="添加小红书账号", font=("Arial", 14, "bold")).pack(pady=10)
        
        form_frame = ttk.Frame(dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 账号
        ttk.Label(form_frame, text="账号 (手机号/邮箱):").grid(row=0, column=0, sticky=W, pady=5)
        username_entry = ttk.Entry(form_frame, width=40)
        username_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        # 密码
        ttk.Label(form_frame, text="密码:").grid(row=1, column=0, sticky=W, pady=5)
        password_entry = ttk.Entry(form_frame, width=40, show="*")
        password_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # 手机号
        ttk.Label(form_frame, text="手机号 (可选):").grid(row=2, column=0, sticky=W, pady=5)
        phone_entry = ttk.Entry(form_frame, width=40)
        phone_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
        
        # 备注
        ttk.Label(form_frame, text="备注:").grid(row=3, column=0, sticky=W, pady=5)
        notes_entry = ttk.Entry(form_frame, width=40)
        notes_entry.grid(row=3, column=1, pady=5, padx=(10, 0))
        
        def on_save():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            phone = phone_entry.get().strip()
            notes = notes_entry.get().strip()
            
            if not username or not password:
                messagebox.showwarning("警告", "账号和密码不能为空")
                return
            
            try:
                # 如果是首次添加，需要设置主密码
                if not self.account_manager.accounts_file.exists():
                    # 生成随机主密码
                    import secrets
                    master_password = secrets.token_urlsafe(16)
                    self.account_manager.encryption.set_master_password(master_password)
                    self.account_manager._master_password_set = True
                    
                    # 显示主密码
                    msg = f"首次设置 - 已生成随机主密码：\n\n{master_password}\n\n⚠️ 请妥善保管此密码，丢失后将无法恢复！"
                    messagebox.showinfo("主密码", msg)
                else:
                    # 验证主密码
                    password = self.account_manager.setup_master_password()
                    if not password:
                        return
                
                # 添加账号
                self.account_manager.add_account(username, password, phone, notes)
                messagebox.showinfo("成功", f"账号已添加：{username}")
                self.refresh_account_list()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("错误", f"添加账号失败：{e}")
        
        ttk.Button(dialog, text="保存", command=on_save).pack(pady=20)
    
    def show_account_manager(self):
        """显示账号管理器"""
        # 这里可以创建一个完整的账号管理窗口
        messagebox.showinfo("提示", "请使用命令行管理账号:\n\npython3 xhs_account_manager.py list\npython3 xhs_account_manager.py add")
    
    def clear_login_states(self):
        """清除登录状态"""
        if messagebox.askyesno("确认", "确定要清除所有登录状态吗？\n\n清除后需要重新登录。"):
            try:
                # 删除所有状态文件
                state_dir = Path("xhs_account_states")
                if state_dir.exists():
                    for f in state_dir.glob("*.json"):
                        f.unlink()
                
                # 删除旧的状态文件
                old_state = Path("xhs_browser_state.json")
                if old_state.exists():
                    old_state.unlink()
                
                self.log("已清除所有登录状态", "success")
                
            except Exception as e:
                self.log(f"清除登录状态失败：{e}", "error")
    
    def start_monitoring(self):
        """开始监控"""
        if self.task_running:
            messagebox.showwarning("警告", "监控任务已在运行中")
            return
        
        # 获取配置
        try:
            keywords_text = self.keywords_text.get("1.0", tk.END).strip()
            keywords = [k.strip() for k in keywords_text.split("\n") if k.strip()]
            
            if not keywords:
                messagebox.showwarning("警告", "请至少输入一个关键词")
                return
            
            max_posts = int(self.max_posts_var.get())
            if max_posts <= 0:
                raise ValueError("帖子数必须大于 0")
            
            period_map = {
                "1_day": MonitorPeriod.ONE_DAY,
                "3_days": MonitorPeriod.THREE_DAYS,
                "1_week": MonitorPeriod.ONE_WEEK,
                "2_weeks": MonitorPeriod.TWO_WEEKS,
                "1_month": MonitorPeriod.ONE_MONTH
            }
            period = period_map.get(self.period_var.get(), MonitorPeriod.ONE_WEEK)
            
        except ValueError as e:
            messagebox.showerror("错误", f"配置错误：{e}")
            return
        
        # 检查账号
        if not self.account_manager.accounts_file.exists():
            if not messagebox.askyesno("确认", "未检测到账号配置，是否现在添加？"):
                return
            self.show_add_account_dialog()
            return
        
        # 创建配置
        self.current_config = MonitorConfig(
            keywords=keywords,
            monitor_period=period,
            max_posts_per_keyword=max_posts,
            extract_comments=self.extract_comments_var.get(),
            headless=self.headless_var.get()
        )
        
        # 启动任务
        self.task_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar.start()
        self.status_label.config(text="运行中", foreground="blue")
        
        self.log(f"开始监控，关键词：{', '.join(keywords)}", "info")
        self.log(f"时间范围：{self.period_var.get()}, 最大帖子数：{max_posts}", "info")
        
        # 在后台线程运行
        self.task_thread = threading.Thread(target=self.run_monitoring, daemon=True)
        self.task_thread.start()
    
    def run_monitoring(self):
        """运行监控任务 (后台线程)"""
        try:
            # 验证主密码
            if not self.account_manager.encryption.is_initialized():
                # 如果没有初始化，尝试加载
                if self.account_manager.encryption.salt_file.exists():
                    # 需要在主线程验证密码
                    self.root.after(0, lambda: self.verify_master_password_for_task())
                    return
            
            # 创建监控器
            monitor = XiaohongshuBrowserMonitor(
                self.current_config,
                account_manager=self.account_manager
            )
            
            # 运行监控
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(monitor.run())
                
                # 更新 UI
                self.root.after(0, lambda: self.on_monitoring_complete(results))
                
            finally:
                loop.close()
                
        except Exception as e:
            self.root.after(0, lambda: self.on_monitoring_error(e))
    
    def verify_master_password_for_task(self):
        """为任务验证主密码"""
        password = self.account_manager.setup_master_password()
        if not password:
            self.log("主密码验证失败，任务取消", "error")
            self.stop_monitoring()
            return
        
        # 重新运行监控
        self.task_thread = threading.Thread(target=self.run_monitoring, daemon=True)
        self.task_thread.start()
    
    def on_monitoring_complete(self, results):
        """监控完成回调"""
        self.task_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.status_label.config(text="已完成", foreground="green")
        
        # 更新统计
        stats = results.get("stats", {})
        self.keywords_count_label.config(text=str(stats.get("keywords_processed", 0)))
        self.posts_count_label.config(text=str(stats.get("total_posts", 0)))
        self.comments_count_label.config(text=str(stats.get("total_comments", 0)))
        
        self.log(f"监控完成，收集帖子：{stats.get('total_posts', 0)}, 评论：{stats.get('total_comments', 0)}", "success")
        
        # 显示结果路径
        export_path = results.get("export_path", "未知")
        self.log(f"结果已保存至：{export_path}", "success")
        
        messagebox.showinfo("完成", f"监控任务已完成!\n\n帖子：{stats.get('total_posts', 0)}\n评论：{stats.get('total_comments', 0)}\n\n结果已保存。")
    
    def on_monitoring_error(self, error):
        """监控错误回调"""
        self.task_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.status_label.config(text="错误", foreground="red")
        
        self.log(f"监控任务出错：{error}", "error")
        messagebox.showerror("错误", f"监控任务失败:\n{error}")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.task_running:
            return
        
        self.task_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.status_label.config(text="已停止", foreground="orange")
        
        self.log("监控任务已停止", "warning")
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def open_results_dir(self):
        """打开结果目录"""
        results_dir = Path("xhs_browser_data")
        if results_dir.exists():
            os.system(f"open {results_dir}")
        else:
            messagebox.showinfo("提示", "结果目录不存在，请先运行监控任务")
    
    def export_config(self):
        """导出配置"""
        keywords = self.keywords_text.get("1.0", tk.END).strip()
        config = {
            "keywords": keywords.split("\n"),
            "period": self.period_var.get(),
            "max_posts": self.max_posts_var.get(),
            "extract_comments": self.extract_comments_var.get(),
            "headless": self.headless_var.get(),
            "auto_rotate": self.auto_rotate_var.get()
        }
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.log(f"配置已导出：{filepath}", "success")
    
    def import_config(self):
        """导入配置"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.keywords_text.delete("1.0", tk.END)
                self.keywords_text.insert("1.0", "\n".join(config.get("keywords", [])))
                self.period_var.set(config.get("period", "1_week"))
                self.max_posts_var.set(str(config.get("max_posts", 30)))
                self.extract_comments_var.set(config.get("extract_comments", True))
                self.headless_var.set(config.get("headless", False))
                self.auto_rotate_var.set(config.get("auto_rotate", True))
                
                self.log(f"配置已导入：{filepath}", "success")
                
            except Exception as e:
                messagebox.showerror("错误", f"导入配置失败：{e}")
    
    def show_help(self):
        """显示帮助"""
        help_text = """
小红书监控器使用说明

1. 添加账号:
   - 点击"添加账号"按钮
   - 输入小红书账号 (手机号/邮箱) 和密码
   - 可选填写手机号和备注

2. 配置搜索:
   - 在关键词框中输入要搜索的关键词 (每行一个)
   - 选择时间范围 (最近 1 天/3 天/1 周等)
   - 设置每关键词最大帖子数

3. 开始监控:
   - 点击"开始监控"按钮
   - 程序会自动登录账号并执行搜索
   - 实时查看日志和统计信息

4. 查看结果:
   - 监控完成后点击"打开结果目录"
   - 结果保存为 JSON 和 CSV 格式

注意事项:
- 首次使用会生成随机主密码，请妥善保管
- 建议启用自动轮换功能 (多账号时)
- 无头模式在后台运行，不显示浏览器
"""
        messagebox.showinfo("使用说明", help_text)
    
    def show_about(self):
        """显示关于"""
        about_text = """
小红书监控器 v2.0

功能特性:
- 多账号管理和自动轮换
- AES-256 加密存储密码
- 自动登录和搜索
- 拟人化行为模拟
- 反检测保护

技术栈:
- Python + Tkinter GUI
- Playwright 浏览器自动化
- AES-256 加密

© 2026 All Rights Reserved
"""
        messagebox.showinfo("关于", about_text)
    
    def on_closing(self):
        """关闭窗口处理"""
        if self.task_running:
            if messagebox.askokcancel("确认", "监控任务正在运行，确定要退出吗？"):
                self.stop_monitoring()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()
    app = XiaohongshuMonitorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
