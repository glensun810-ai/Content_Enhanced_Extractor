# 快速启动指南

## 启动方式

### 方式 1: 直接启动 GUI (推荐)

```bash
python3 main.py
```

**默认启动统一 GUI 界面**，包含：
- ✅ 通用网站内容提取
- ✅ 小红书监控器 (多账号自动版)
- ✅ 账号管理

### 方式 2: 使用命令行参数

```bash
# 启动小红书监控器 GUI
python3 main.py --xhs-gui

# 启动通用网站提取器 GUI
python3 main.py --gui

# 启动小红书监控器命令行
python3 main.py --xhs-cli

# 启动账号管理
python3 main.py --account

# 显示命令行菜单
python3 main.py --menu
```

### 方式 3: 使用快捷脚本

```bash
# macOS/Linux
./start_xhs_monitor.sh

# Windows
start_xhs_monitor.bat
```

## 查看帮助

```bash
python3 main.py --help
```

输出:
```
网站内容提取工具集

options:
  -h, --help  show this help message and exit
  --gui       启动通用网站提取器 GUI
  --xhs-gui   启动小红书监控器 GUI
  --xhs-cli   启动小红书监控器命令行
  --account   启动账号管理
  --menu      显示命令行菜单
  --no-check  跳过依赖检查

示例:
  python3 main.py              启动统一 GUI 界面 (默认)
  python3 main.py --menu       显示命令行菜单
  python3 main.py --gui        启动通用网站提取器 GUI
  python3 main.py --xhs-gui    启动小红书监控器 GUI
  python3 main.py --xhs-cli    启动小红书监控器命令行
  python3 main.py --account    启动账号管理
```

## GUI 界面说明

### 统一 GUI 界面布局

```
┌─────────────────────────────────────────────────────┐
│ Multimodal Website Content Extractor                │
├─────────────────────────────────────────────────────┤
│ [Extraction] [Text Docs] [Multi Docs]              │
│ [小红书监控器] [About]                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  切换到不同标签页使用对应功能：                      │
│                                                     │
│  • Extraction     - 通用网站内容提取                │
│  • Text Docs      - 文本文档管理                    │
│  • Multi Docs     - 多模态文档管理                  │
│  • 小红书监控器   - 小红书监控 (多账号自动版)       │
│  • About          - 关于                            │
└─────────────────────────────────────────────────────┘
```

### 小红书监控器标签页

切换到"小红书监控器"标签页后：

```
┌─────────────────────────────────────────────────────┐
│ 账号配置                                            │
│ 选择账号：[自动轮换 ▼] [刷新] [添加] [管理]        │
│ ☑ 启用自动轮换 (推荐)                              │
│ 总账号：3, 可用：2, 冷却中：1                      │
├─────────────────────────────────────────────────────┤
│ 搜索配置                                            │
│ 关键词：                                            │
│ ┌─────────────────────────────────────────────┐    │
│ │ GEO 优化                                     │    │
│ │ AI 搜索排名                                  │    │
│ │ 品牌获客                                     │    │
│ └─────────────────────────────────────────────┘    │
│ 时间范围：[最近 1 周 ▼]                              │
│ ☑ 提取评论  ☐ 无头模式                              │
├─────────────────────────────────────────────────────┤
│ [开始监控] [停止监控] [清空日志] [打开结果目录]    │
│ ████████████░░░░░░░░ 进度条                         │
├─────────────────────────────────────────────────────┤
│ 运行状态                                            │
│ 当前状态：运行中  关键词：2/3                       │
│ 帖子：85  评论：230  当前账号：acc_001             │
├─────────────────────────────────────────────────────┤
│ 运行日志                                            │
│ [10:30:15] 开始监控...                              │
│ [10:30:20] 使用账号：138****8000                   │
│ [10:30:25] 自动登录成功！                          │
│ ...                                                 │
└─────────────────────────────────────────────────────┘
```

## 常见问题

### Q: 为什么运行 main.py 没有弹出窗口？

**A**: 可能的原因：

1. **tkinter 未安装**
   ```bash
   # macOS
   brew install python-tk
   
   # Linux
   sudo apt-get install python3-tk
   ```

2. **在 SSH 或无显示环境中运行**
   - 使用命令行模式：`python3 main.py --menu`
   - 或在本地有显示环境的机器上运行

3. **依赖检查失败**
   - 使用 `--no-check` 跳过：`python3 main.py --no-check`

### Q: 如何返回命令行菜单？

**A**: 使用 `--menu` 参数：
```bash
python3 main.py --menu
```

### Q: 如何快速启动小红书监控器？

**A**: 有三种方式：
```bash
# 方式 1: 直接启动小红书监控 GUI
python3 main.py --xhs-gui

# 方式 2: 使用快捷脚本
./start_xhs_monitor.sh

# 方式 3: 启动统一 GUI 后切换标签页
python3 main.py
# 然后切换到"小红书监控器"标签页
```

## 启动流程对比

### 之前 (多个独立入口)

```bash
# 需要记住不同的命令
python3 gui_interface.py          # 通用提取器
python3 xhs_monitor_gui.py        # 小红书监控 GUI
python3 xhs_browser_monitor.py    # 小红书监控命令行
python3 xhs_account_manager.py    # 账号管理
```

### 现在 (统一入口)

```bash
# 一个命令即可
python3 main.py                   # 默认启动统一 GUI

# 或使用参数指定
python3 main.py --xhs-gui         # 小红书监控 GUI
python3 main.py --menu            # 命令行菜单
```

## 推荐启动方式

| 使用场景 | 推荐命令 |
|---------|---------|
| 日常使用 | `python3 main.py` |
| 只需要小红书监控 | `python3 main.py --xhs-gui` |
| SSH/远程连接 | `python3 main.py --menu` |
| 批量处理 | `python3 main.py --xhs-cli` |

---

**提示**: 首次使用建议使用 GUI 界面，操作更直观。熟悉后可以使用命令行参数快速启动特定功能。
