"""
Website Text Extractor Tool

This tool extracts all text content from a specified website and packages it into
a structured document for AI knowledge base construction.
"""

import os
import sys
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
from pathlib import Path
import argparse


class WebsiteTextExtractor:
    def __init__(self, base_url, max_pages=50, delay=1):
        """
        Initialize the website text extractor
        
        Args:
            base_url (str): The base URL of the website to extract text from
            max_pages (int): Maximum number of pages to scrape
            delay (float): Delay between requests in seconds to be respectful
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.delay = delay
        self.visited_urls = set()
        self.to_visit = [base_url]
        self.text_content = {}
        
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
            not url.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.exe', '.dmg'))
        )
    
    def extract_text_from_page(self, url):
        """Extract text content from a single webpage"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text from important elements
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ""
            
            headings = []
            for i in range(1, 7):  # h1 to h6
                for heading in soup.find_all(f'h{i}'):
                    headings.append(heading.get_text(strip=True))
            
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
            
            # Get text from other content elements
            divs = [div.get_text(strip=True) for div in soup.find_all('div', class_=lambda x: x and 'content' in x.lower())]
            articles = [article.get_text(strip=True) for article in soup.find_all('article')]
            sections = [section.get_text(strip=True) for section in soup.find_all('section')]
            
            # Combine all text content
            all_text = {
                'url': url,
                'title': title_text,
                'headings': headings,
                'paragraphs': paragraphs,
                'divs': divs,
                'articles': articles,
                'sections': sections
            }
            
            return all_text
            
        except Exception as e:
            print(f"Error extracting text from {url}: {str(e)}")
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
    
    def extract_all_text(self):
        """Extract text from all pages in the website"""
        print(f"Starting to extract text from {self.base_url}")
        print(f"Will visit up to {self.max_pages} pages with {self.delay}s delay between requests")
        
        pages_processed = 0
        
        while self.to_visit and pages_processed < self.max_pages:
            current_url = self.to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
                
            print(f"Processing: {current_url}")
            
            # Extract text from current page
            text_data = self.extract_text_from_page(current_url)
            if text_data:
                self.text_content[current_url] = text_data
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
        
        print(f"Completed extraction. Processed {len(self.text_content)} pages.")
        return self.text_content
    
    def save_to_document(self, output_path="website_text_output.txt"):
        """Save extracted text to a structured document"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Website Text Extraction Report\n")
            f.write(f"Base URL: {self.base_url}\n")
            f.write(f"Extraction Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Number of Pages Processed: {len(self.text_content)}\n")
            f.write("="*80 + "\n\n")
            
            for url, content in self.text_content.items():
                f.write(f"URL: {url}\n")
                f.write("-"*80 + "\n")
                
                if content['title']:
                    f.write(f"Title: {content['title']}\n\n")
                
                if content['headings']:
                    f.write("Headings:\n")
                    for heading in content['headings']:
                        f.write(f"  - {heading}\n")
                    f.write("\n")
                
                if content['paragraphs']:
                    f.write("Paragraphs:\n")
                    for paragraph in content['paragraphs']:
                        if paragraph:  # Skip empty paragraphs
                            f.write(f"  {paragraph}\n\n")
                
                if content['articles'] or content['sections'] or content['divs']:
                    f.write("Additional Content:\n")
                    for article in content['articles']:
                        if article:
                            f.write(f"  Article: {article}\n")
                    for section in content['sections']:
                        if section:
                            f.write(f"  Section: {section}\n")
                    for div in content['divs']:
                        if div:
                            f.write(f"  Div: {div}\n")
                    f.write("\n")
                
                f.write("\n" + "="*80 + "\n\n")
        
        print(f"Text content saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract text content from a website for AI knowledge base construction")
    parser.add_argument("url", help="The base URL of the website to extract text from")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum number of pages to scrape (default: 50)")
    parser.add_argument("--delay", type=float, default=1, help="Delay between requests in seconds (default: 1)")
    parser.add_argument("--output", default="website_text_output.txt", help="Output file path (default: website_text_output.txt)")
    
    args = parser.parse_args()
    
    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)
    
    # Check if required packages are available
    try:
        import requests
        import bs4
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Please install them using: pip install requests beautifulsoup4")
        sys.exit(1)
    
    # Create extractor and run
    extractor = WebsiteTextExtractor(args.url, args.max_pages, args.delay)
    extractor.extract_all_text()
    extractor.save_to_document(args.output)
    
    print(f"\nExtraction complete! Output saved to {args.output}")


if __name__ == "__main__":
    main()