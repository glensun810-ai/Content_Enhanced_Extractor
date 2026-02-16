"""
Multimodal Website Content Extractor Tool

This tool extracts text, images, and preserves the structure of web pages
for comprehensive AI knowledge base construction.
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


class MultimodalDocumentManager:
    """Manages storage and retrieval of multimodal documents"""
    
    def __init__(self, storage_dir="multimodal_docs"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.images_dir = self.storage_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        self.metadata_file = self.storage_dir / "metadata.json"
        self.documents = self.load_documents()
    
    def load_documents(self):
        """Load document metadata from file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_documents(self):
        """Save document metadata to file"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
    
    def add_document(self, doc_id, url, title, content, images_info, timestamp=None):
        """Add a new multimodal document to the manager"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Create content file
        content_file = f"{doc_id}_content.txt"
        content_path = self.storage_dir / content_file
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save images
        image_files = []
        for img_info in images_info:
            img_filename = img_info['filename']
            img_path = self.images_dir / img_filename
            with open(img_path, 'wb') as f:
                f.write(img_info['data'])
            image_files.append(str(img_path))
        
        # Store document metadata
        self.documents[doc_id] = {
            'url': url,
            'title': title,
            'timestamp': timestamp,
            'content_file': content_file,
            'image_files': image_files,
            'image_count': len(image_files)
        }
        
        self.save_documents()
    
    def get_document(self, doc_id):
        """Get multimodal document content by ID"""
        if doc_id not in self.documents:
            return None
        
        # Read content
        content_file = self.storage_dir / self.documents[doc_id]['content_file']
        if content_file.exists():
            with open(content_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = ""
        
        # Get image info
        image_files = self.documents[doc_id].get('image_files', [])
        
        return {
            'url': self.documents[doc_id]['url'],
            'title': self.documents[doc_id]['title'],
            'timestamp': self.documents[doc_id]['timestamp'],
            'content': content,
            'image_files': image_files,
            'image_count': self.documents[doc_id]['image_count']
        }
    
    def list_documents(self):
        """List all stored documents"""
        return [
            {
                'id': doc_id,
                'url': doc['url'],
                'title': doc['title'],
                'timestamp': doc['timestamp'],
                'image_count': doc.get('image_count', 0)
            }
            for doc_id, doc in self.documents.items()
        ]
    
    def delete_document(self, doc_id):
        """Delete a multimodal document by ID"""
        if doc_id not in self.documents:
            return False
        
        # Delete content file
        content_file = self.storage_dir / self.documents[doc_id]['content_file']
        if content_file.exists():
            content_file.unlink()
        
        # Delete associated images
        for img_file in self.documents[doc_id].get('image_files', []):
            img_path = Path(img_file)
            if img_path.exists():
                img_path.unlink()
        
        # Remove from metadata
        del self.documents[doc_id]
        self.save_documents()
        return True


class MultimodalWebsiteExtractor:
    def __init__(self, base_url, max_pages=20, delay=1, save_images=True):
        """
        Initialize the multimodal website extractor
        
        Args:
            base_url (str): The base URL of the website to extract content from
            max_pages (int): Maximum number of pages to scrape
            delay (float): Delay between requests in seconds to be respectful
            save_images (bool): Whether to download and save images
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.delay = delay
        self.save_images = save_images
        self.visited_urls = set()
        self.to_visit = [base_url]
        self.page_contents = {}  # Store content for each page
        
        # Create headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def is_valid_url(self, url):
        """Check if the URL is valid and belongs to the same domain"""
        parsed = urlparse(url)
        return (
            parsed.netloc == self.domain and
            url not in self.visited_urls and
            not url.endswith(('.pdf', '.zip', '.exe', '.dmg'))
        )
    
    def download_image(self, img_url, page_domain):
        """Download an image from the given URL"""
        try:
            # Handle relative URLs
            full_img_url = urljoin(page_domain, img_url)
            
            response = requests.get(full_img_url, headers=self.headers, timeout=10)
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
        """Extract all content (text, images, structure) from a single webpage"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
            videos = [vid.get('src') for vid in soup.find_all(['video', 'iframe']) if vid.get('src')]
            
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
            
            # Compile all content
            page_content = {
                'url': url,
                'title': title,
                'headings': headings,
                'paragraphs': paragraphs,
                'divs': divs,
                'articles': articles,
                'sections': sections,
                'links': links,
                'images': images,
                'videos': videos,
                'structure': structure
            }
            
            return page_content
            
        except Exception as e:
            print(f"Error extracting content from {url}: {str(e)}")
            return None
    
    def get_links_from_page(self, url):
        """Extract all links from a webpage that belong to the same domain"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
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
        print(f"Starting multimodal extraction from {self.base_url}")
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
    
    def generate_multimodal_document(self):
        """Generate a structured multimodal document from extracted content"""
        content = f"Multimodal Website Content Extraction Report\n"
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
                for i, paragraph in enumerate(data['paragraphs']):
                    if paragraph:  # Skip empty paragraphs
                        content += f"  {i+1}. {paragraph}\n\n"
            
            # Add other content
            if data['articles']:
                content += "ARTICLES:\n"
                for article in data['articles']:
                    if article:
                        content += f"  - {article}\n"
                content += "\n"
            
            if data['sections']:
                content += "SECTIONS:\n"
                for section in data['sections']:
                    if section:
                        content += f"  - {section}\n"
                content += "\n"
            
            if data['divs']:
                content += "CONTENT DIVS:\n"
                for div in data['divs']:
                    if div:
                        content += f"  - {div}\n"
                content += "\n"
            
            # Add links
            if data['links']:
                content += "LINKS FOUND:\n"
                for link in data['links'][:10]:  # Limit to first 10 links
                    content += f"  - [{link['text']}]({link['url']})\n"
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
                for video in data['videos']:
                    content += f"  - {video}\n"
                content += "\n"
            
            # Add structural information
            structure = data['structure']
            content += "STRUCTURAL INFORMATION:\n"
            content += f"  Tag counts: {dict(list(structure['tag_counts'].items())[:10])}\n"  # Top 10 tags
            content += f"  Classes used: {list(structure['classes_used'])[:10]}{'...' if len(structure['classes_used']) > 10 else ''}\n"
            content += f"  IDs used: {list(structure['ids_used'])[:10]}{'...' if len(structure['ids_used']) > 10 else ''}\n"
            
            content += "\n" + "="*80 + "\n\n"
        
        content += f"\nSUMMARY:\n"
        content += f"- Total pages processed: {len(self.page_contents)}\n"
        content += f"- Total images extracted: {total_images}\n"
        
        return content, [{'filename': img['filename'], 'data': img['data']} 
                         for page_data in self.page_contents.values() 
                         for img in page_data['images']]


def main():
    parser = argparse.ArgumentParser(description="Extract multimodal content from a website for AI knowledge base construction")
    parser.add_argument("url", help="The base URL of the website to extract content from")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum number of pages to scrape (default: 20)")
    parser.add_argument("--delay", type=float, default=1, help="Delay between requests in seconds (default: 1)")
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
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Please install them using: pip install -r requirements.txt")
        print("Note: For OCR functionality, you also need to install Tesseract OCR separately")
        sys.exit(1)
    
    # Create extractor and run
    extractor = MultimodalWebsiteExtractor(
        args.url, 
        args.max_pages, 
        args.delay, 
        save_images=not args.no_images
    )
    extractor.extract_all_content()
    
    # Generate multimodal document
    content, images_info = extractor.generate_multimodal_document()
    
    # Create document ID
    doc_id = f"multi_doc_{int(time.time())}"
    
    # Get a title for the document
    title = urlparse(args.url).netloc
    if extractor.page_contents:
        first_title = next(iter(extractor.page_contents.values()))['title']
        if first_title:
            title = first_title[:50] + "..." if len(first_title) > 50 else first_title
    
    # Store the document using the multimodal document manager
    doc_manager = MultimodalDocumentManager()
    doc_manager.add_document(doc_id, args.url, title, content, images_info)
    
    print(f"\nMultimodal extraction complete!")
    print(f"Document ID: {doc_id}")
    print(f"Title: {title}")
    print(f"Pages processed: {len(extractor.page_contents)}")
    print(f"Images extracted: {sum(len(page_data['images']) for page_data in extractor.page_contents.values())}")
    print(f"Content saved to document manager.")


if __name__ == "__main__":
    main()