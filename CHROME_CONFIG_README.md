# Chrome 浏览器路径配置说明

## 问题原因
Playwright 默认会查找 Chromium 浏览器，但你的系统中安装的是 Google Chrome。需要配置使用正确的浏览器路径。

## 已修复的文件

以下文件已更新，配置了正确的 Chrome 浏览器路径：

### 1. xhs_browser_monitor.py
```python
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

### 2. xhs_init.py
```python
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

### 3. xhs_monitoring_service.py
```python
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

## 验证配置

运行以下命令验证配置是否正确：

```bash
python3 -c "
from xhs_browser_monitor import CHROME_PATH
import os
print(f'Chrome 路径：{CHROME_PATH}')
print(f'文件存在：{os.path.exists(CHROME_PATH)}')
"
```

输出应该显示：
```
Chrome 路径：/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
文件存在：True
```

## 使用方法

### 方法 1: GUI 界面（推荐）

```bash
python launcher.py
```

然后在 GUI 中：
1. 选择 "Xiaohongshu Monitor" 标签页
2. 选择 "Browser-based" 模式
3. 输入关键词
4. 点击 "Start Monitoring"

### 方法 2: 快速启动脚本

```bash
python run_xhs_monitor.py
```

### 方法 3: 登录初始化

首次使用建议先登录：

```bash
python xhs_init.py
```

这会让你在浏览器中登录小红书，并保存登录状态。

### 方法 4: 编程接口

```python
import asyncio
from xhs_browser_monitor import XiaohongshuBrowserMonitor, MonitorConfig, MonitorPeriod

async def main():
    config = MonitorConfig(
        keywords=["你的关键词 1", "你的关键词 2", "你的关键词 3"],
        monitor_period=MonitorPeriod.ONE_WEEK,
        max_posts_per_keyword=50,
        extract_comments=True,
        headless=False
    )
    
    monitor = XiaohongshuBrowserMonitor(config)
    results = await monitor.run()
    
    print(f"找到 {len(results['posts'])} 篇帖子")

asyncio.run(main())
```

## 注意事项

1. **首次运行**：会弹出 Chrome 浏览器窗口，需要手动登录小红书
2. **登录状态**：登录成功后会保存到 `xhs_browser_state.json`，下次无需重复登录
3. **浏览器窗口**：不要关闭弹出的浏览器窗口，直到监控完成
4. **网络要求**：确保能够访问小红书网站 (https://www.xiaohongshu.com)

## 常见问题

### 问题 1: 找不到 Chrome 浏览器
确保 Chrome 安装在默认路径：
```
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
```

如果安装在其他位置，请修改配置文件中的 `CHROME_PATH`。

### 问题 2: 登录状态失效
删除状态文件重新登录：
```bash
rm xhs_browser_state.json
python xhs_init.py
```

### 问题 3: 监控结果为空
- 检查关键词是否正确
- 扩大监控时间范围
- 确认登录状态有效

## 文件清单

已修改的文件：
- ✅ xhs_browser_monitor.py
- ✅ xhs_init.py
- ✅ xhs_monitoring_service.py
- ✅ gui_interface.py (已集成浏览器监控)

新增的文件：
- ✅ run_xhs_monitor.py (快速启动脚本)
- ✅ CHROME_CONFIG_README.md (本文档)
