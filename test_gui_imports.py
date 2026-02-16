#!/usr/bin/env python3
"""
Test script to verify that the GUI interface can import all required modules
"""

def test_imports():
    print("Testing imports for GUI interface...")
    
    try:
        from enhanced_web_text_extractor import InteractiveExtractor, DocumentManager, MultimodalDocumentManager
        print("✓ Enhanced web text extractor imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import enhanced web text extractor: {e}")
        return False
    
    try:
        from multimodal_web_extractor import MultimodalWebsiteExtractor
        print("✓ Multimodal web extractor imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import multimodal web extractor: {e}")
        return False
    
    try:
        from web_text_extractor import WebsiteTextExtractor
        print("✓ Web text extractor imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import web text extractor: {e}")
        return False
    
    try:
        from js_dynamic_extractor import SpecializedJSDynamicExtractor
        print("✓ JS dynamic extractor imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import JS dynamic extractor: {e}")
        return False
    
    try:
        from xiaohongshu_scraper import XiaohongshuScraper, XiaohongshuScraperConfig
        print("✓ Xiaohongshu scraper imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Xiaohongshu scraper: {e}")
        return False
    
    try:
        from xiaohongshu_monitoring_service import XiaohongshuMonitoringService, MonitoringConfig, MonitoringStatus
        print("✓ Xiaohongshu monitoring service imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Xiaohongshu monitoring service: {e}")
        return False
    
    print("\nAll imports successful! The GUI should work correctly with the new JS dynamic extractor.")
    return True

if __name__ == "__main__":
    test_imports()