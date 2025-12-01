# PDF Book Crawler

A specialized web crawler designed to discover and catalog PDF books with intelligent metadata extraction and CSV export functionality.

## Features

- 🔍 **Intelligent Book Detection**: Uses machine learning-inspired patterns to identify likely book PDFs
- 📖 **Metadata Extraction**: Automatically extracts title, author, ISBN, publication year from filenames
- 📊 **Confidence Scoring**: Assigns confidence scores to discovered books based on multiple factors
- 📁 **CSV Export**: Exports discovered books to structured CSV with all metadata
- 🎯 **Configurable Crawling**: Adjustable depth, page limits, and file size thresholds
- 📈 **Progress Tracking**: Comprehensive logging and discovery statistics
- 🧪 **Fully Tested**: Complete unit test coverage

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Settings (Optional)

Edit `Configuration/config.ini` to customize:

```ini
[BookCrawler]
# Minimum file size in MB to consider as a potential book
min-book-size-mb=1.0
# Extract PDF metadata when possible  
extract-pdf-metadata=true
# Patterns that indicate a file is likely a book
book-patterns=["(?i).*\\b(book|ebook|manual|guide|tutorial|textbook)\\b.*", "(?i).*\\b(chapter|volume|edition)\\b.*"]

[Filenames]
# CSV output file for discovered books
book-csv-output=discovered_books.csv
```

### 3. Run the Example

```bash
python example_book_crawler.py
```

Or use the crawler programmatically:

```python
from Core.config_manager import IniConfigManager
from Core.http_client import RequestsHttpClient  
from Core.scraper import Scraper
from Core.pdf_book_crawler import PDFBookCrawler

# Initialize components
config_manager = IniConfigManager()
http_client = RequestsHttpClient(config_manager.get_user_agent())
scraper = Scraper(config_manager, http_client)
book_crawler = PDFBookCrawler(config_manager, http_client, scraper)

# Crawl for books
discovered_books = book_crawler.crawl_for_books(
    start_url="https://example.com/books",
    max_depth=3,      # Crawl up to 3 levels deep
    max_pages=100     # Visit up to 100 pages
)

# Export results
csv_file = book_crawler.export_books_to_csv()
print(f"Exported {len(discovered_books)} books to {csv_file}")

# Get summary statistics
summary = book_crawler.get_discovery_summary()
print(f"Found {summary['total_books']} books with {summary['average_confidence']:.2f} avg confidence")
```

## How It Works

### 1. Intelligent Book Classification

The crawler uses multiple heuristics to identify PDF books:

- **Filename Patterns**: Looks for keywords like "book", "manual", "guide", "textbook"
- **Link Text Analysis**: Examines anchor text for book-related terms
- **File Size**: Considers minimum size thresholds (books are typically larger)
- **Author Detection**: Uses regex patterns to extract author names
- **ISBN Recognition**: Identifies ISBN numbers in filenames
- **Title Extraction**: Intelligently parses titles from filenames

### 2. Confidence Scoring

Each discovered book receives a confidence score (0.0-1.0) based on:

- ✅ **Book keywords found** (+0.3)
- ✅ **Link text indicates book** (+0.2)  
- ✅ **Author extracted** (+0.2)
- ✅ **ISBN found** (+0.3)
- ✅ **File size ≥ minimum** (+0.2)
- ✅ **Publication year found** (+0.1)
- ❌ **Very small file** (-0.3)

### 3. Metadata Extraction

Automatically extracts metadata using smart patterns:

```python
# Title extraction examples:
"Python_Programming_Guide.pdf" → "Python Programming Guide"
"Machine-Learning-Basics.pdf" → "Machine Learning Basics"

# Author extraction examples:  
"Python_by_John_Doe.pdf" → "John Doe"
"Deep_Learning-Ian_Goodfellow.pdf" → "Ian Goodfellow"

# ISBN detection:
"isbn9781234567890_python_book.pdf" → "9781234567890"
```

## Output Format

The CSV export includes these columns:

| Column | Description | Example |
|--------|-------------|---------|
| Title | Extracted book title | "Python Programming Guide" |
| Author | Extracted author name | "John Doe" |
| Website | Source website domain | "example.com" |  
| Source URL | Direct PDF download link | "https://example.com/book.pdf" |
| File Size (MB) | Estimated file size | "2.50" |
| Crawl Date | When book was discovered | "2024-01-01 12:00:00" |
| Confidence Score | Classification confidence | "0.85" |
| ISBN | Extracted ISBN if found | "9781234567890" |
| Publication Year | Extracted year if found | "2024" |

## Configuration Options

### Crawling Parameters

```python
discovered_books = book_crawler.crawl_for_books(
    start_url="https://example.com",
    max_depth=3,        # How deep to crawl (default: 3)
    max_pages=100       # Maximum pages to visit (default: 100) 
)
```

### Book Classification Settings

Customize in `config.ini`:

```ini
[BookCrawler]
min-book-size-mb=1.0                    # Minimum file size threshold
extract-pdf-metadata=true               # Enable metadata extraction
book-patterns=[".*book.*", ".*manual.*"] # Custom book detection patterns
```

## Testing

Run the comprehensive test suite:

```bash
python -m unittest Tests.test_pdf_book_crawler -v
```

Tests cover:
- ✅ Book metadata creation and CSV export
- ✅ PDF link detection and classification  
- ✅ Title and author extraction algorithms
- ✅ Confidence scoring logic
- ✅ Website crawling and link following
- ✅ Error handling and edge cases

## Architecture

The PDF Book Crawler follows the existing project's dependency injection pattern:

```
PDFBookCrawler
├── ConfigManager (configuration management)
├── HttpClient (HTTP requests and responses) 
├── Scraper (HTML parsing and link extraction)
└── BookMetadata (data structure for book info)
```

Key design principles:
- **Single Responsibility**: Each class has one focused purpose
- **Dependency Injection**: All dependencies injected via constructor
- **Testability**: Easy to mock dependencies for unit testing
- **Configuration-Driven**: Behavior controlled via config files
- **Logging**: Comprehensive logging for debugging and monitoring

## Use Cases

Perfect for discovering books from:

- 📚 **Academic repositories** (university digital libraries)
- 📖 **Open source documentation** (project manuals and guides)  
- 🏫 **Educational websites** (course materials and textbooks)
- 🔬 **Research platforms** (technical papers and reports)
- 📄 **Documentation sites** (API docs and tutorials)

## Limitations

- Only discovers publicly accessible PDF links
- Classification accuracy depends on filename quality
- Limited to same-domain crawling by default
- No OCR or PDF content analysis (filename-based only)
- Respects robots.txt and rate limiting

## Contributing

1. Add new book detection patterns in `Configuration/config.ini`
2. Extend metadata extraction in `_classify_and_extract_book_metadata()`
3. Add tests for new functionality in `Tests/test_pdf_book_crawler.py`
4. Follow existing code patterns and dependency injection

## License

Same as the main Scraper project.