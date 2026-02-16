"""
Specialized Dynamic Content Extractor for JavaScript-Heavy Websites

This tool is specifically designed to extract content from websites
that use JavaScript frameworks like Vue.js, React, and Angular for dynamic content loading.
"""

import os
import sys
import json
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
from pathlib import Path
import argparse
from datetime import datetime
import base64
from PIL import Image
from io import BytesIO
import pytesseract
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import re


class SpecializedJSDynamicExtractor:
    def __init__(self, base_url, wait_time=20):
        """
        Initialize the specialized extractor for JavaScript-heavy websites

        Args:
            base_url (str): The URL of the website to extract content from
            wait_time (int): Time to wait for page to load and render
        """
        self.base_url = base_url
        self.wait_time = wait_time
        self.page_content = {}

        # Setup Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        try:
            # Automatically download and setup ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except WebDriverException as e:
            print(f"Error initializing Chrome driver: {e}")
            print("Make sure you have Chrome installed")
            raise

    def __del__(self):
        """Clean up the webdriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def extract_content_from_page(self, url):
        """Extract all content from the JavaScript-heavy webpage using Selenium"""
        try:
            print(f"Accessing: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            print("Waiting for page to load...")
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait additional time for dynamic content to load
            print("Waiting for dynamic content...")
            time.sleep(5)
            
            # Scroll to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Get page source after JavaScript execution
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract page title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Extract headings
            headings = {}
            for i in range(1, 7):  # h1 to h6
                headings[f'h{i}'] = [h.get_text(strip=True) for h in soup.find_all(f'h{i}')]

            # Extract paragraphs
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]

            # Extract text from various elements
            divs = [div.get_text(strip=True) for div in soup.find_all('div') if div.get_text(strip=True)]
            articles = [article.get_text(strip=True) for article in soup.find_all('article')]
            sections = [section.get_text(strip=True) for section in soup.find_all('section')]
            spans = [span.get_text(strip=True) for span in soup.find_all('span') if span.get_text(strip=True)]
            lis = [li.get_text(strip=True) for li in soup.find_all('li')]
            strongs = [strong.get_text(strip=True) for strong in soup.find_all('strong')]
            ems = [em.get_text(strip=True) for em in soup.find_all('em')]
            asides = [aside.get_text(strip=True) for aside in soup.find_all('aside')]
            navs = [nav.get_text(strip=True) for nav in soup.find_all('nav')]
            headers = [header.get_text(strip=True) for header in soup.find_all('header')]
            footers = [footer.get_text(strip=True) for footer in soup.find_all('footer')]

            # Extract navigation/menu items specifically
            nav_items = []
            for nav_elem in soup.find_all(['nav', 'ul', 'ol'], class_=re.compile(r'menu|nav|header|footer|sidebar', re.I)):
                nav_items.extend([item.get_text(strip=True) for item in nav_elem.find_all('a')])
            
            # Extract button texts
            buttons = [btn.get_text(strip=True) for btn in soup.find_all('button')]
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                link_text = link.get_text(strip=True)
                if link_text:  # Only add links with text
                    links.append({'url': full_url, 'text': link_text})

            # Extract images
            images = []
            for img in soup.find_all('img'):
                img_src = img.get('src')
                if img_src and not img_src.startswith('data:'):  # Skip data URLs
                    img_alt = img.get('alt', '')
                    img_title = img.get('title', '')
                    
                    images.append({
                        'src': img_src,
                        'alt': img_alt,
                        'title': img_title
                    })

            # Extract form elements (inputs, selects, etc.)
            forms = []
            for form in soup.find_all(['input', 'select', 'textarea']):
                if form.get('name') or form.get('placeholder') or form.get('value'):
                    forms.append({
                        'type': form.name,
                        'name': form.get('name', ''),
                        'placeholder': form.get('placeholder', ''),
                        'value': form.get('value', ''),
                        'id': form.get('id', '')
                    })

            # Extract all text content as a single block
            all_text = soup.get_text()
            # Clean up text
            lines = (line.strip() for line in all_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = ' '.join(chunk for chunk in chunks if chunk)

            # Compile all content
            page_content = {
                'url': url,
                'title': title,
                'headings': headings,
                'paragraphs': paragraphs,
                'divs': divs,
                'articles': articles,
                'sections': sections,
                'spans': spans,
                'lists': lis,
                'strongs': strongs,
                'ems': ems,
                'asides': asides,
                'navs': navs,
                'headers': headers,
                'footers': footers,
                'nav_items': nav_items,
                'buttons': buttons,
                'links': links,
                'images': images,
                'forms': forms,
                'all_text': clean_text
            }

            return page_content

        except Exception as e:
            print(f"Error extracting content from {url}: {str(e)}")
            return None

    def extract_all_content(self):
        """Extract content from the website"""
        print(f"Starting specialized JavaScript-heavy extraction from {self.base_url}")

        # Extract content from the main page
        content_data = self.extract_content_from_page(self.base_url)
        if content_data:
            self.page_content[self.base_url] = content_data

        print(f"Completed extraction from {self.base_url}.")
        return self.page_content

    def generate_detailed_report(self):
        """Generate a detailed report of the extracted content"""
        content = f"JavaScript-Heavy Website Content Extraction Report\n"
        content += f"URL: {self.base_url}\n"
        content += f"Extraction Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += "="*80 + "\n\n"

        for url, data in self.page_content.items():
            content += f"PAGE: {url}\n"
            content += "="*80 + "\n"

            if data['title']:
                content += f"TITLE: {data['title']}\n\n"

            # Add headings
            for level, headings in data['headings'].items():
                if headings:
                    content += f"{level.upper()} HEADINGS:\n"
                    for heading in headings:
                        content += f"  - {heading}\n"
                    content += "\n"

            # Add paragraphs
            if data['paragraphs']:
                content += "PARAGRAPHS:\n"
                for i, paragraph in enumerate(data['paragraphs']):
                    if paragraph:  # Skip empty paragraphs
                        content += f"  {i+1}. {paragraph}\n\n"

            # Add navigation items
            if data['nav_items']:
                content += f"NAVIGATION ITEMS ({len(data['nav_items'])} found):\n"
                for i, nav_item in enumerate(data['nav_items']):
                    content += f"  {i+1}. {nav_item}\n"
                content += "\n"

            # Add buttons
            if data['buttons']:
                content += f"BUTTONS ({len(data['buttons'])} found):\n"
                for i, button in enumerate(data['buttons']):
                    content += f"  {i+1}. {button}\n"
                content += "\n"

            # Add links
            if data['links']:
                content += f"LINKS ({len(data['links'])} found):\n"
                for i, link in enumerate(data['links']):
                    content += f"  {i+1}. {link['text']} -> {link['url']}\n"
                content += "\n"

            # Add images
            if data['images']:
                content += f"IMAGES ({len(data['images'])} found):\n"
                for i, img in enumerate(data['images']):
                    content += f"  {i+1}. Source: {img['src']}\n"
                    if img['alt']:
                        content += f"     Alt text: {img['alt']}\n"
                    if img['title']:
                        content += f"     Title: {img['title']}\n\n"

            # Add forms
            if data['forms']:
                content += f"FORM ELEMENTS ({len(data['forms'])} found):\n"
                for i, form in enumerate(data['forms']):
                    content += f"  {i+1}. Type: {form['type']}, Name: {form['name']}, Placeholder: {form['placeholder']}\n"
                content += "\n"

            # Add all text content
            content += "FULL TEXT CONTENT:\n"
            content += data['all_text']
            content += "\n\n"
            content += "="*80 + "\n\n"

        return content


def main():
    parser = argparse.ArgumentParser(description="Extract content from JavaScript-heavy websites which use dynamic content loading")
    parser.add_argument("url", help="The URL of the JavaScript-heavy website to extract content from")
    parser.add_argument("--wait-time", type=int, default=20, help="Time to wait for page to load (default: 20)")

    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)

    # Check if required packages are available
    try:
        import requests
        import bs4
        from PIL import Image
        import pytesseract
        from selenium import webdriver
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Please install them using: pip install -r requirements.txt")
        sys.exit(1)

    # Create extractor and run
    extractor = SpecializedJSDynamicExtractor(
        args.url,
        wait_time=args.wait_time
    )
    
    try:
        extractor.extract_all_content()

        # Generate detailed report
        content = extractor.generate_detailed_report()

        # Create output directory if it doesn't exist
        output_dir = Path("specialized_extraction_output")
        output_dir.mkdir(exist_ok=True)

        # Save content to file
        output_file = output_dir / f"js_dynamic_extraction_{int(time.time())}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\nSpecialized JavaScript-heavy extraction complete!")
        print(f"Content saved to: {output_file}")
        print(f"Pages processed: {len(extractor.page_content)}")

    except Exception as e:
        print(f"Error during extraction: {str(e)}")
    finally:
        # Ensure driver is closed
        if hasattr(extractor, 'driver'):
            extractor.driver.quit()


if __name__ == "__main__":
    main()