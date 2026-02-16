# Xiaohongshu Browser-based Monitoring System

## Overview

This system allows you to monitor Xiaohongshu (Little Red Book) for posts and comments related to specific keywords by leveraging a manually logged-in browser session. The system provides both a GUI interface and programmatic API for monitoring.

## Features

- **Manual Login Support**: Users can log in to Xiaohongshu via browser (using phone verification or QR code)
- **Session Persistence**: Login state is saved locally for reuse
- **Keyword Monitoring**: Search for multiple keywords and extract relevant posts
- **Time-based Filtering**: Filter posts by monitoring period (1 day, 3 days, 1 week, 2 weeks, 1 month, custom)
- **Comment Extraction**: Optionally extract comments from posts
- **Multiple Export Formats**: Export results to JSON, CSV, or Excel
- **GUI Interface**: User-friendly interface for configuration and monitoring
- **Stealth Mode**: Uses playwright-stealth to avoid bot detection

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GUI Interface                                 │
│  - Keywords input (3-5 keywords)                                 │
│  - Monitor Period selection                                      │
│  - Max posts configuration                                       │
│  - Start/Stop controls                                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           Browser Monitor Service                                │
│  - Manages browser lifecycle                                     │
│  - Handles async execution                                       │
│  - Provides progress callbacks                                   │
│  - Status management                                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              Browser Controller                                  │
│  - Launches Chromium browser                                     │
│  - Loads/saves session state (cookies)                           │
│  - Ensures login status                                          │
│  - Navigates to search pages                                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           Search & Extraction                                    │
│  - Searches keywords on Xiaohongshu                              │
│  - Extracts post metadata (title, author, likes, etc.)           │
│  - Extracts comments (optional)                                  │
│  - Parses timestamps                                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           Time-based Filter                                      │
│  - Filters posts by monitor period                               │
│  - Handles relative time formats (刚刚，分钟前，小时前，天前)         │
│  - Handles absolute date formats                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           Data Storage & Export                                  │
│  - Saves results to JSON                                         │
│  - Exports to CSV/Excel                                          │
│  - Organizes by date and keyword                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install Playwright specifically:

```bash
pip install playwright playwright-stealth
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Initialize Login (Optional)

You can pre-login using the initialization script:

```bash
python xhs_init.py
```

This will:
1. Open a browser window
2. Allow you to log in to Xiaohongshu
3. Save the login state to `xhs_state.json`

## Usage

### Method 1: GUI Interface (Recommended)

1. Run the launcher:
```bash
python launcher.py
```

2. Or run the GUI directly:
```bash
python gui_interface.py
```

3. Navigate to the "Xiaohongshu Monitor" tab

4. Select "Browser-based (Requires Login)" mode

5. Enter 3-5 keywords to monitor

6. Select monitoring period:
   - 1 day
   - 3 days
   - 1 week
   - 2 weeks
   - 1 month
   - Custom (specify number of days)

7. Configure max posts per keyword

8. Optionally enable comment extraction

9. Click "Start Monitoring"

10. A browser window will open:
    - If not logged in, complete login manually
    - The system will search for each keyword
    - Posts and comments will be extracted
    - Results will be displayed in the GUI

11. Export results using the export buttons

### Method 2: Programmatic API

```python
import asyncio
from xhs_browser_monitor import XiaohongshuBrowserMonitor, MonitorConfig, MonitorPeriod

async def main():
    # Configure monitoring
    config = MonitorConfig(
        keywords=["GEO 优化", "AI 搜索排名", "品牌获客"],
        monitor_period=MonitorPeriod.ONE_WEEK,
        max_posts_per_keyword=50,
        extract_comments=True,
        headless=False  # Show browser for login
    )
    
    # Create and run monitor
    monitor = XiaohongshuBrowserMonitor(config)
    results = await monitor.run()
    
    print(f"Found {len(results['posts'])} posts")
    print(f"Found {len(results['comments'])} comments")

asyncio.run(main())
```

### Method 3: Quick Monitor Function

```python
import asyncio
from xhs_browser_monitor import quick_monitor

async def main():
    results = await quick_monitor(
        keywords=["GEO 优化", "AI 搜索"],
        period="1_week",
        max_posts=50,
        extract_comments=True,
        headless=False
    )
    
    print(f"Results saved to: {results.get('export_path')}")

asyncio.run(main())
```

### Method 4: Using the Service Layer

```python
from xhs_browser_monitor_service import XiaohongshuBrowserMonitorService

def on_complete(result):
    print(f"Completed! Found {len(result.posts)} posts")

def on_error(error):
    print(f"Error: {error}")

# Create service
service = XiaohongshuBrowserMonitorService()
service.on_complete = on_complete
service.on_error = on_error

# Start monitoring
service.start_monitoring(
    keywords=["GEO 优化", "AI 搜索"],
    monitor_period="1_week",
    max_posts_per_keyword=50,
    extract_comments=True,
    headless=False
)
```

## File Structure

```
xhs_browser_monitor.py          # Core browser monitoring logic
xhs_browser_monitor_service.py  # Service layer for GUI integration
xhs_init.py                     # Login initialization script
xhs_monitoring_service.py       # Legacy monitoring service (updated)
xhs_browser_data/               # Data storage directory
├── posts/                      # Saved post data
├── comments/                   # Saved comment data
├── exports/                    # Exported CSV/Excel files
└── monitor_result_*.json       # Complete monitoring results
xhs_browser_state.json          # Saved login session
```

## Data Formats

### Post Data

```json
{
  "id": "xhs_1234567890_001",
  "title": "帖子标题",
  "description": "帖子描述",
  "author_nickname": "作者昵称",
  "author_id": "author_123",
  "url": "https://www.xiaohongshu.com/explore/...",
  "timestamp": "2 小时前",
  "timestamp_unix": 1234567890000,
  "like_count": 1234,
  "collect_count": 567,
  "comment_count": 89,
  "share_count": 12,
  "tags": ["#标签 1", "#标签 2"],
  "images": ["image_url_1", "image_url_2"],
  "keyword": "匹配的关键词",
  "extracted_at": "2024-01-15T10:30:00"
}
```

### Comment Data

```json
{
  "id": "comment_1234567890_001",
  "post_id": "xhs_1234567890_001",
  "post_title": "帖子标题",
  "content": "评论内容",
  "author_nickname": "评论作者",
  "author_id": "commenter_123",
  "timestamp": "1 小时前",
  "timestamp_unix": 1234567890000,
  "like_count": 45,
  "keyword": "匹配的关键词",
  "extracted_at": "2024-01-15T10:30:00"
}
```

## Time Format Support

The system supports various time formats from Xiaohongshu:

- **Relative**: 刚刚，5 分钟前，2 小时前，3 天前，昨天，前天
- **Absolute**: 2024-01-15, 2024/01/15, 01-15, 01/15

## Monitoring Modes

### Browser-based Mode (Recommended)
- Uses your actual logged-in Xiaohongshu session
- Extracts real-time data from the platform
- Requires manual login (one-time)
- More accurate and up-to-date results

### API/Mock Mode
- Uses simulated data for demonstration
- No login required
- Useful for testing the interface
- Not suitable for production use

## Best Practices

1. **Login Once**: Use `xhs_init.py` to pre-login and save session
2. **Reasonable Limits**: Don't extract too many posts at once (50-100 per keyword recommended)
3. **Respect Rate Limits**: The system includes built-in delays to avoid triggering anti-bot measures
4. **Regular Sessions**: Re-login periodically as sessions may expire
5. **Monitor Period**: Use appropriate time ranges for your needs

## Troubleshooting

### Login Issues
- Clear the `xhs_browser_state.json` file and re-login
- Try using phone verification instead of QR code
- Ensure you complete login in the browser window

### No Results Found
- Check if keywords are too specific
- Try expanding the monitoring period
- Verify that the browser is properly logged in

### Extraction Errors
- Check network connection
- Ensure Xiaohongshu website is accessible
- Try running in non-headless mode to see what's happening

### Performance Issues
- Reduce max posts per keyword
- Disable comment extraction if not needed
- Use shorter monitoring periods

## Security Notes

- Login state is stored locally in `xhs_browser_state.json`
- Keep this file secure and don't share it
- The system only accesses publicly available data
- No credentials are stored in the code

## License

This tool is for educational and research purposes. Please respect Xiaohongshu's terms of service and use responsibly.
