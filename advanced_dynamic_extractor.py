"""
Advanced Dynamic Website Content Extractor

This tool extracts content from dynamic websites that use JavaScript to render content,
such as Vue.js, React, Angular, and other SPA frameworks.
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


class AdvancedDynamicExtractor:
    def __init__(self, base_url, max_pages=10, delay=2, save_images=True, wait_time=10):
        """
        Initialize the advanced dynamic website extractor

        Args:
            base_url (str): The base URL of the website to extract content from
            max_pages (int): Maximum number of pages to scrape
            delay (float): Delay between requests in seconds to be respectful
            save_images (bool): Whether to download and save images
            wait_time (int): Time to wait for page to load and render
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.delay = delay
        self.save_images = save_images
        self.wait_time = wait_time
        self.visited_urls = set()
        self.to_visit = [base_url]
        self.page_contents = {}  # Store content for each page

        # Setup Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
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

    def is_valid_url(self, url):
        """Check if the URL is valid and belongs to the same domain"""
        parsed = urlparse(url)
        return (
            parsed.netloc == self.domain and
            url not in self.visited_urls and
            not url.endswith(('.pdf', '.zip', '.exe', '.dmg', '.doc', '.docx', '.xls', '.xlsx'))
        )

    def wait_for_page_load(self):
        """Wait for page to be fully loaded"""
        try:
            # Wait for the body element to be present
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait a bit more for dynamic content to load
            time.sleep(3)

            # Scroll to bottom to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

        except TimeoutException:
            print(f"Timeout waiting for page to load, continuing anyway...")

    def download_image(self, img_url, page_domain):
        """Download an image from the given URL"""
        try:
            # Handle relative URLs
            full_img_url = urljoin(page_domain, img_url)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(full_img_url, headers=headers, timeout=10)
            response.raise_for_status()

            return response.content
        except Exception as e:
            print(f"Error downloading image {img_url}: {str(e)}")
            return None

    def extract_text_from_image(self, image_data):
        """Extract text from image using OCR"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(BytesIO(image_data))

            # Perform OCR
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            print(f"OCR failed for image: {str(e)}")
            return ""

    def extract_content_from_page(self, url):
        """Extract all content (text, images, structure) from a single webpage using Selenium"""
        try:
            print(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            self.wait_for_page_load()

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

            # Extract other text elements
            divs = [div.get_text(strip=True) for div in soup.find_all('div', class_=lambda x: x and 'content' in x.lower())]
            articles = [article.get_text(strip=True) for article in soup.find_all('article')]
            sections = [section.get_text(strip=True) for section in soup.find_all('section')]
            
            # Extract text from other common content containers
            spans = [span.get_text(strip=True) for span in soup.find_all('span')]
            lis = [li.get_text(strip=True) for li in soup.find_all('li')]
            strongs = [strong.get_text(strip=True) for strong in soup.find_all('strong')]
            ems = [em.get_text(strip=True) for em in soup.find_all('em')]
            asides = [aside.get_text(strip=True) for aside in soup.find_all('aside')]
            navs = [nav.get_text(strip=True) for nav in soup.find_all('nav')]
            headers = [header.get_text(strip=True) for header in soup.find_all('header')]
            footers = [footer.get_text(strip=True) for footer in soup.find_all('footer')]

            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                link_text = link.get_text(strip=True)
                links.append({'url': full_url, 'text': link_text})

            # Extract images
            images = []
            if self.save_images:
                for img in soup.find_all('img'):
                    img_src = img.get('src')
                    if img_src:
                        # Handle data URLs
                        if img_src.startswith('data:'):
                            continue  # Skip data URLs for now
                        
                        img_alt = img.get('alt', '')
                        img_title = img.get('title', '')

                        # Download image data
                        img_data = self.download_image(img_src, url)
                        if img_data:
                            # Generate filename
                            img_filename = f"img_{int(time.time())}_{len(images)}.jpg"

                            # Extract text from image using OCR
                            img_text = self.extract_text_from_image(img_data)

                            images.append({
                                'src': img_src,
                                'alt': img_alt,
                                'title': img_title,
                                'filename': img_filename,
                                'data': img_data,
                                'ocr_text': img_text
                            })

            # Extract other media (videos, iframes, etc.)
            videos = []
            for vid in soup.find_all(['video', 'iframe', 'source']):
                if vid.get('src'):
                    videos.append(vid.get('src'))
                elif vid.get('data-src'):
                    videos.append(vid.get('data-src'))

            # Preserve some structural information
            structure = {
                'tag_counts': {},
                'classes_used': set(),
                'ids_used': set()
            }

            for tag in soup.find_all():
                tag_name = tag.name
                if tag_name:
                    structure['tag_counts'][tag_name] = structure['tag_counts'].get(tag_name, 0) + 1

                classes = tag.get('class', [])
                if classes:
                    structure['classes_used'].update(classes)

                tag_id = tag.get('id')
                if tag_id:
                    structure['ids_used'].add(tag_id)

            # Also extract text that might be in Vue.js/react-style attributes or data attributes
            vue_react_text = []
            for element in soup.find_all(attrs={"data-v-*": True}):  # Vue.js attributes
                for attr, value in element.attrs.items():
                    if attr.startswith('data-v-') and isinstance(value, str):
                        vue_react_text.append(value)
            
            # Find text in elements that might be dynamically populated
            dynamic_elements = soup.find_all(lambda tag: tag.name in ['div', 'span', 'p', 'li'] and 
                                           not tag.find_all() and 
                                           tag.get_text(strip=True))
            dynamic_texts = [elem.get_text(strip=True) for elem in dynamic_elements 
                           if len(elem.get_text(strip=True)) > 10]  # Only longer texts

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
                'links': links,
                'images': images,
                'videos': videos,
                'vue_react_text': vue_react_text,
                'dynamic_texts': dynamic_texts,
                'structure': structure
            }

            return page_content

        except Exception as e:
            print(f"Error extracting content from {url}: {str(e)}")
            return None

    def get_links_from_page(self, url):
        """Extract all links from a webpage that belong to the same domain using Selenium"""
        try:
            self.driver.get(url)
            self.wait_for_page_load()

            # Get page source after JavaScript execution
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)

                if self.is_valid_url(full_url):
                    links.append(full_url)

            return links

        except Exception as e:
            print(f"Error getting links from {url}: {str(e)}")
            return []

    def extract_all_content(self):
        """Extract content from all pages in the website"""
        print(f"Starting advanced dynamic extraction from {self.base_url}")
        print(f"Will visit up to {self.max_pages} pages with {self.delay}s delay between requests")

        pages_processed = 0

        while self.to_visit and pages_processed < self.max_pages:
            current_url = self.to_visit.pop(0)

            if current_url in self.visited_urls:
                continue

            print(f"Processing: {current_url}")

            # Extract content from current page
            content_data = self.extract_content_from_page(current_url)
            if content_data:
                self.page_contents[current_url] = content_data
                pages_processed += 1

            # Add current URL to visited set
            self.visited_urls.add(current_url)

            # Get links from current page and add to to_visit if not visited
            links = self.get_links_from_page(current_url)
            for link in links:
                if link not in self.visited_urls and link not in self.to_visit:
                    self.to_visit.append(link)

            # Respectful delay between requests
            time.sleep(self.delay)

        print(f"Completed extraction. Processed {len(self.page_contents)} pages.")
        return self.page_contents

    def generate_comprehensive_document(self):
        """Generate a comprehensive document from extracted content"""
        content = f"Advanced Dynamic Website Content Extraction Report\n"
        content += f"Base URL: {self.base_url}\n"
        content += f"Extraction Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"Number of Pages Processed: {len(self.page_contents)}\n"
        content += "="*80 + "\n\n"

        total_images = 0

        for url, data in self.page_contents.items():
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
                for i, paragraph in enumerate(data['paragraphs'][:50]):  # Limit to first 50 to avoid too much text
                    if paragraph:  # Skip empty paragraphs
                        content += f"  {i+1}. {paragraph}\n\n"

            # Add other content elements
            content_elements = [
                ('SPANS', data['spans']),
                ('LIST ITEMS', data['lists']),
                ('STRONG/BOLD TEXT', data['strongs']),
                ('ITALIC TEXT', data['ems']),
                ('ASIDE CONTENT', data['asides']),
                ('NAVIGATION', data['navs']),
                ('HEADERS', data['headers']),
                ('FOOTERS', data['footers']),
                ('SECTIONS', data['sections']),
                ('ARTICLES', data['articles']),
                ('DIVS', data['divs']),
                ('DYNAMIC TEXTS', data['dynamic_texts']),
                ('VUE/REACT ATTRIBUTES', data['vue_react_text'])
            ]
            
            for label, elements in content_elements:
                if elements:
                    content += f"{label}:\n"
                    for i, element in enumerate(elements[:20]):  # Limit to first 20 to avoid too much text
                        if element and len(element.strip()) > 1:  # Skip very short elements
                            content += f"  {i+1}. {element}\n"
                    if len(elements) > 20:
                        content += f"  ... and {len(elements) - 20} more {label.lower()}\n"
                    content += "\n"

            # Add links
            if data['links']:
                content += "LINKS FOUND:\n"
                for i, link in enumerate(data['links'][:10]):  # Limit to first 10 links
                    content += f"  {i+1}. {link['text']} -> {link['url']}\n"
                if len(data['links']) > 10:
                    content += f"  ... and {len(data['links']) - 10} more links\n"
                content += "\n"

            # Add images
            if data['images']:
                content += f"IMAGES ({len(data['images'])} found):\n"
                for i, img in enumerate(data['images']):
                    content += f"  {i+1}. Source: {img['src']}\n"
                    if img['alt']:
                        content += f"     Alt text: {img['alt']}\n"
                    if img['title']:
                        content += f"     Title: {img['title']}\n"
                    if img['ocr_text']:
                        content += f"     OCR Text: {img['ocr_text']}\n"
                    content += f"     Filename: {img['filename']}\n\n"

                total_images += len(data['images'])

            # Add videos/iframes
            if data['videos']:
                content += "VIDEOS/IFRAMES:\n"
                for i, video in enumerate(data['videos']):
                    content += f"  {i+1}. {video}\n"
                content += "\n"

            # Add structural information
            structure = data['structure']
            content += "STRUCTURAL INFORMATION:\n"
            content += f"  Tag counts: {dict(list(structure['tag_counts'].items())[:15])}\n"  # Top 15 tags
            content += f"  Classes used: {list(structure['classes_used'])[:15]}{'...' if len(structure['classes_used']) > 15 else ''}\n"
            content += f"  IDs used: {list(structure['ids_used'])[:15]}{'...' if len(structure['ids_used']) > 15 else ''}\n"

            content += "\n" + "="*80 + "\n\n"

        content += f"\nSUMMARY:\n"
        content += f"- Total pages processed: {len(self.page_contents)}\n"
        content += f"- Total images extracted: {total_images}\n"

        return content, [{'filename': img['filename'], 'data': img['data']}
                         for page_data in self.page_contents.values()
                         for img in page_data['images']]


def main():
    parser = argparse.ArgumentParser(description="Extract content from dynamic websites that use JavaScript for rendering")
    parser.add_argument("url", help="The base URL of the website to extract content from")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum number of pages to scrape (default: 10)")
    parser.add_argument("--delay", type=float, default=2, help="Delay between requests in seconds (default: 2)")
    parser.add_argument("--wait-time", type=int, default=10, help="Time to wait for page to load (default: 10)")
    parser.add_argument("--no-images", action='store_true', help="Don't download and process images")

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
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Please install them using: pip install -r requirements.txt")
        print("Note: For this tool, you also need to install ChromeDriver")
        sys.exit(1)

    # Create extractor and run
    extractor = AdvancedDynamicExtractor(
        args.url,
        args.max_pages,
        args.delay,
        save_images=not args.no_images,
        wait_time=args.wait_time
    )
    
    try:
        extractor.extract_all_content()

        # Generate comprehensive document
        content, images_info = extractor.generate_comprehensive_document()

        # Create output directory if it doesn't exist
        output_dir = Path("advanced_extraction_output")
        output_dir.mkdir(exist_ok=True)

        # Save content to file
        output_file = output_dir / f"advanced_extraction_{int(time.time())}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\nAdvanced dynamic extraction complete!")
        print(f"Content saved to: {output_file}")
        print(f"Pages processed: {len(extractor.page_contents)}")
        print(f"Images extracted: {sum(len(page_data['images']) for page_data in extractor.page_contents.values())}")

    except Exception as e:
        print(f"Error during extraction: {str(e)}")
    finally:
        # Ensure driver is closed
        if hasattr(extractor, 'driver'):
            extractor.driver.quit()


if __name__ == "__main__":
    main()