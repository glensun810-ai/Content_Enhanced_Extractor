# Multimodal Website Content Extractor

A comprehensive Python tool that extracts text, images, and preserves the structure of web pages for AI knowledge base construction. The tool offers both text-only and multimodal extraction capabilities with multiple interfaces (GUI and command-line) for managing extracted content.

## Features

- Extracts text content from all pages within a domain
- Downloads and processes images from web pages
- Extracts text from images using OCR (Optical Character Recognition)
- Preserves original webpage structure and metadata
- Follows internal links up to a specified limit
- Multiple interfaces: GUI and interactive command-line
- Stores and manages multiple extractions (both text-only and multimodal)
- View, save, and delete extracted documents
- Outputs to structured text documents
- Respects robots.txt and includes delays between requests
- Filters out non-text content (executables, etc.)
- Specialized JavaScript dynamic content extraction for modern SPAs (Single Page Applications)
- Supports websites built with Vue.js, React, Angular, and other JavaScript frameworks
- Waits for dynamic content to load before extraction

## Requirements

- Python 3.6+
- `requests` library
- `beautifulsoup4` library
- `Pillow` library
- `pytesseract` library
- `tkinter` library (usually comes with Python)
- Tesseract OCR engine (separate installation required)

## Installation

1. Clone or download this repository
2. Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install requests beautifulsoup4 Pillow pytesseract
```

3. Install Tesseract OCR engine (required for image text extraction):

- **On macOS** (using Homebrew):
  ```bash
  brew install tesseract
  ```

- **On Ubuntu/Debian**:
  ```bash
  sudo apt-get install tesseract-ocr
  ```

- **On Windows**: Download from [Tesseract at UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

### GUI Interface (Recommended for beginners)

Run the GUI launcher to access the graphical interface:

```bash
python launcher.py
```

Then click "Launch GUI Interface" to open the visual tool with:
- Easy form-based extraction controls
- Tabs for managing text and multimodal documents
- Visual progress indicators
- Integrated viewer for extracted content

### Main Menu (Command-Line)

Run the main menu to access all command-line tools:

```bash
python main.py
```

This will present options for:
1. Enhanced Interactive Tool (Multimodal) - Text-based menu
2. Basic Command-Line Tool (Text Only)
3. Multimodal Command-Line Tool
4. Exit

### Interactive Mode (Multimodal)

Run the enhanced interactive tool:

```bash
python enhanced_web_text_extractor.py
```

This will launch an interactive menu with the following options:

1. Extract text-only content from a website
2. Extract multimodal content from a website (text + images + structure)
3. View extracted documents
4. View specific document
5. Delete a document
6. Save document to external file
7. View multimodal documents
8. View specific multimodal document
9. Delete multimodal document
10. Exit

### Command-Line Usage

#### Text-Only Extraction:
```bash
python web_text_extractor.py <website_url>
```

With custom options:
```bash
python web_text_extractor.py https://example.com --max-pages 30 --delay 1.5 --output my_extraction.txt
```

#### Multimodal Extraction:
```bash
python multimodal_web_extractor.py <website_url>
```

With custom options:
```bash
python multimodal_web_extractor.py https://example.com --max-pages 10 --delay 1.0 --no-images
```

#### JavaScript Dynamic Content Extraction:
```bash
python js_dynamic_extractor.py <website_url>
```

With custom options:
```bash
python js_dynamic_extractor.py https://example.com --wait-time 25
```

### Command-Line Options

#### Text-Only Tool Options:
- `url`: The base URL of the website to extract text from (required)
- `--max-pages`: Maximum number of pages to scrape (default: 50)
- `--delay`: Delay between requests in seconds (default: 1)
- `--output`: Output file path (default: website_text_output.txt)

#### Multimodal Tool Options:
- `url`: The base URL of the website to extract content from (required)
- `--max-pages`: Maximum number of pages to scrape (default: 20)
- `--delay`: Delay between requests in seconds (default: 1)
- `--no-images`: Don't download and process images

## GUI Interface Features

### 1. Extraction Tab
- Simple form for entering website URL
- Configurable options for max pages and delay
- Choice between text-only, multimodal, and JavaScript dynamic extraction
- Real-time progress indicator
- Output log showing extraction progress
- Customizable wait time for JavaScript-heavy sites

### 2. Text Documents Tab
- List view of all text-only extractions
- Document ID, title, and timestamp
- Actions: View, Delete, Save to file

### 3. Multimodal Documents Tab
- List view of all multimodal extractions
- Document ID, title, timestamp, and image count
- Actions: View, Delete, Save to file

### 4. About Tab
- Information about the tool and its features
- Usage instructions

## Interactive Tool Features

### 1. Text-Only Extraction
- Prompts for a website URL
- Allows setting maximum pages to scan
- Configurable delay between requests
- Automatically stores the extraction with a unique ID

### 2. Multimodal Extraction
- Extracts text, images, and structural information
- Downloads images and performs OCR to extract text from them
- Preserves webpage structure and metadata
- Stores images separately with references in the document

### 3. Document Management
- View all extracted documents (text-only or multimodal)
- View specific documents by ID
- Delete unwanted documents
- Save documents to external files

## Output Format

### Text-Only Documents
The tool creates a structured text document with:
- Base URL and extraction metadata
- Individual sections for each page containing:
  - Page URL
  - Title
  - Headings (h1-h6)
  - Paragraphs
  - Additional content from articles, sections, and divs

### Multimodal Documents
The tool creates:
- A structured text document with:
  - Base URL and extraction metadata
  - Page-by-page content including titles, headings, paragraphs
  - Links found on each page
  - Information about images (source, alt text, title, OCR-extracted text)
  - Structural information (HTML tags, CSS classes, IDs)
- Separate image files stored in the `images/` subdirectory
- Metadata file tracking all document information

## Example Workflow

### GUI Approach:
1. Run the launcher: `python launcher.py`
2. Click "Launch GUI Interface"
3. Enter URL in the "Extract Content" tab
4. Set options (max pages, delay, content type)
5. Click "Extract Content"
6. Monitor progress in the output panel
7. Switch to "Text Documents" or "Multimodal Documents" tab to manage results

### Command-Line Approach:
1. Run the main menu: `python main.py`
2. Select option 1 for the enhanced interactive tool
3. Choose option 2 to perform multimodal extraction
4. Enter the URL (e.g., https://example.com)
5. Set maximum pages (e.g., 10) and delay (e.g., 1.0)
6. Choose whether to save images (enables OCR processing)
7. Wait for extraction to complete
8. Select option 7 to see all multimodal documents
9. Select option 8 to view a specific multimodal document by ID
10. Select option 6 to save a document to an external file

## Storage Locations

### Text-Only Documents
Extracted documents are stored in the `extracted_docs/` directory:
- Individual text files for each extraction
- `metadata.json` file to track document information

### Multimodal Documents
Extracted documents are stored in the `multimodal_docs/` directory:
- Individual text content files
- Images stored in the `images/` subdirectory
- `metadata.json` file to track document information

## Important Notes

- Be respectful when scraping websites; follow their robots.txt guidelines
- Adjust the delay parameter to be courteous to the target server
- Large websites may take considerable time to process
- Some websites may have anti-scraping measures that could prevent extraction
- OCR accuracy depends on image quality and text clarity
- The GUI provides an easy-to-use interface for beginners
- The command-line tools offer more control for advanced users

## Creating Standalone Executables

The tools can be packaged as standalone executables for easy distribution without requiring Python installation. This is useful for sharing with users who don't have Python installed.

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Building Executables

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Use the provided build script to create executables:
```bash
python build_executables.py
```

This will create standalone executables in the `dist/` directory:
- `WebsiteTextExtractor` - Interactive application with all features
- `BasicTextExtractor` - Basic command-line text extractor
- `MultimodalExtractor` - Command-line multimodal extractor

### Cross-Platform Distribution

- Executables must be built on the target platform (Windows executables must be built on Windows, macOS executables on macOS)
- The build script automatically detects the platform and creates appropriately named executables
- For OCR functionality, Tesseract OCR must be installed separately on the target system

### Executable Features

- Completely standalone (no Python installation required)
- Include all necessary dependencies
- Same functionality as the Python scripts
- Cross-platform compatibility with the same user interface

## Mobile Web Application

For mobile devices (including iPhone), a web-based version is available that provides the same functionality through any web browser.

### Features
- Mobile-responsive interface that works on all smartphone browsers
- Simulated extraction process with progress indication
- Two extraction modes: Text-only and Multimodal
- Configurable parameters (max pages, delay between requests)

### How to Use
1. Open `iphone_app.html` in any smartphone browser
2. Or host it on a web server and access via URL
3. Enter website URL and configure extraction parameters
4. View simulated extraction results

### Adding to Home Screen (iPhone)
1. Open the page in Safari
2. Tap the Share button
3. Select "Add to Home Screen"
4. Access like a native app from your home screen
### Running Local Server
To serve the mobile web app locally:
```bash
python web_server.py
### Running Local Server
To serve the mobile web app locally:
```bash
python web_server.py
```
Then access via http://localhost:8000/iphone_app.html

## License

This project is open source and available under the MIT License.
