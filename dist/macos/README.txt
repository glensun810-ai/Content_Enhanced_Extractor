# Website Text Extractor Tools

Standalone executables for extracting content from websites.

## Available Tools

1. **WebsiteTextExtractor** - Interactive tool with full features
2. **BasicTextExtractor** - Simple command-line text extractor  
3. **MultimodalExtractor** - Advanced extractor with images and structure

## Platform Information

Built for: Darwin arm64
Build Date: 2026-02-06 19:54:28

## Usage Instructions

### Interactive Mode (WebsiteTextExtractor)
Run without arguments to start the interactive menu:
```
./WebsiteTextExtractor     # On macOS/Linux
WebsiteTextExtractor.exe   # On Windows
```

### Command Line Mode
For automated processing:

**Basic Text Extraction:**
```
./BasicTextExtractor https://example.com --max-pages 10 --delay 1
```

**Multimodal Extraction:**
```
./MultimodalExtractor https://example.com --max-pages 5 --delay 1
```

## Command Line Options

### BasicTextExtractor
- `url` (required): Website URL to extract from
- `--max-pages N`: Maximum number of pages to process (default: 50)
- `--delay SECONDS`: Delay between requests (default: 1)
- `--output FILE`: Output file name (default: website_text_output.txt)

### MultimodalExtractor
- `url` (required): Website URL to extract from
- `--max-pages N`: Maximum number of pages to process (default: 20)
- `--delay SECONDS`: Delay between requests (default: 1)
- `--no-images`: Skip downloading images

## Dependencies

All Python dependencies are bundled in the executables:
- requests
- beautifulsoup4
- Pillow
- pytesseract

## OCR Support (Text from Images)

For OCR functionality to work, you need to install Tesseract OCR separately:

**Windows:** Download installer from https://github.com/UB-Mannheim/tesseract/wiki
**macOS:** `brew install tesseract`
**Linux:** `sudo apt install tesseract-ocr` (Ubuntu/Debian) or equivalent

## Storage

Extracted documents are saved to:
- `extracted_docs/` for text-only documents
- `multimodal_docs/` for multimodal documents

## Troubleshooting

- If executables don't run, check if your antivirus is blocking them (they're safe)
- On macOS, you might need to allow the app in Security & Privacy settings
- Large websites may take considerable time to process
- Respect website terms of service and robots.txt
