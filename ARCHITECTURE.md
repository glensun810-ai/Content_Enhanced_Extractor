# Project Architecture Diagram

## Logical Architecture of Python Files

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              main.py                                        │
│                           (Entry Point)                                     │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           launcher.py                                       │
│                       (GUI/CLI Launcher)                                    │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        gui_interface.py                                     │
│                      (GUI Application)                                      │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     enhanced_web_text_extractor.py                          │
│                    (Interactive Text Extractor)                             │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      multimodal_web_extractor.py                            │
│                    (Multimodal Content Extractor)                           │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      web_text_extractor.py                                  │
│                        (Text Extractor)                                     │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      xiaohongshu_scraper.py                                 │
│                        (Xiaohongshu Scraper)                                │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    real_xiaohongshu_collector.py                            │
│                     (Real Data Collector)                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                  xiaohongshu_monitoring_service.py                          │
│                    (Monitoring Service)                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        xhs_monitoring_service.py                            │
│                      (XHS Monitoring Service)                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           xhs_init.py                                       │
│                        (XHS Initialization)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Dependency Relationships

### Core Components:
- `main.py` → `gui_interface.py`, `web_text_extractor.py`, `multimodal_web_extractor.py`, `xiaohongshu_scraper.py`
- `launcher.py` → `gui_interface.py`
- `gui_interface.py` → `enhanced_web_text_extractor.py`, `multimodal_web_extractor.py`, `web_text_extractor.py`, `xiaohongshu_scraper.py`, `xiaohongshu_monitoring_service.py`
- `enhanced_web_text_extractor.py` → `web_text_extractor.py`, `multimodal_web_extractor.py`
- `multimodal_web_extractor.py` → `web_text_extractor.py`
- `xiaohongshu_scraper.py` → `real_xiaohongshu_collector.py`
- `xiaohongshu_monitoring_service.py` → `xiaohongshu_scraper.py`
- `xhs_monitoring_service.py` → `xiaohongshu_monitoring_service.py`

### Entry Points:
1. `main.py` - Main application entry point with menu options
2. `launcher.py` - GUI/CLI launcher
3. Individual modules can be run independently

### Functional Groups:
- **Core Extraction**: `web_text_extractor.py`, `multimodal_web_extractor.py`, `enhanced_web_text_extractor.py`
- **Xiaohongshu Tools**: `xiaohongshu_scraper.py`, `real_xiaohongshu_collector.py`, `xiaohongshu_monitoring_service.py`, `xhs_monitoring_service.py`, `xhs_init.py`
- **UI Layer**: `main.py`, `launcher.py`, `gui_interface.py`

### Shared Dependencies:
All modules rely on common libraries:
- requests
- BeautifulSoup4
- PIL (for image processing)
- pytesseract (for OCR)
- pandas (for Xiaohongshu tools)
- openpyxl (for Xiaohongshu tools)