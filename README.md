# Web Scraper

A modern Python web scraping application designed to extract and download PDF documents from websites using configurable strategies for different file hosting services. Built with clean architecture principles, dependency injection, and comprehensive testing.

## ✨ Features

### Core Functionality
- 🌐 **Web Scraping**: Parse web pages using CSS selectors, element IDs, classes, or custom attributes
- 📁 **Multi-Host Downloads**: Support for Google Drive, MediaFire, DataFileHost, and direct downloads
- 📎 **PDF Extraction**: Automatically identify and extract PDF document links
- 💾 **Batch Downloads**: Download multiple files with progress tracking and error handling
- 🔄 **Resume Support**: Skip existing files to avoid re-downloads

### Architecture Highlights
- 🏗️ **Modern Architecture**: Dependency injection, strategy pattern, clean separation of concerns
- 🧪 **Fully Testable**: Mock HTTP client, file operations, and configuration for unit testing
- ⚙️ **Configurable**: INI and JSON configuration files for easy customization
- 🔌 **Extensible**: Easy to add new download strategies via plugin registry
- 📊 **Robust Error Handling**: Structured exception hierarchy with contextual information

### Supported Platforms
- **Google Drive**: Handles confirmation cookies and file ID extraction
- **MediaFire**: Extracts download links from MediaFire pages
- **DataFileHost**: Manages session cookies and download endpoints
- **Direct Downloads**: Simple HTTP downloads with progress tracking
- **Archive.org**: Support for Internet Archive downloads

## 🚀 Quick Start

## Azure Function App

The Azure deployment is scraper-only.

- It runs the `pdf_link_scraper` timer trigger on the `SCRAPER_SCHEDULE` cron schedule.
- It scrapes the configured book sites from `SCRAPER_SITES`.
- It writes weekly scrape results to Azure Blob Storage in the configured container, currently `scraped-links`.
- It uploads date-stamped CSV snapshots plus crawl progress JSON so later runs can resume incrementally.

Current blob layout:

```text
{site_name}/{YYYY-MM-DD}/wordpress_scrape.csv
{site_name}/{YYYY-MM-DD}/sitemap_scrape.csv
{site_name}/wordpress_crawl_progress.json
{site_name}/sitemap_crawl_progress.json
```

The CSV downloader remains available as a local script, but it is not deployed as an Azure Function trigger.

### Installation

```bash
git clone https://github.com/hasanrashid/Scraper.git
cd Scraper
pip install -r requirements.txt
```

### Basic Usage

```python
from Core.application import create_scraper_app

# Create application with default configuration
app = create_scraper_app()

# Scrape links from a webpage
links = app.scrape_links(
    'http://example.com',
    element_type='a',
    css_selector='.download-links'
)

# Download a file
result = app.download_file('https://drive.google.com/file/d/abc123/view')

# Download multiple files
urls = ['http://example.com/file1.pdf', 'http://example.com/file2.pdf']
results = app.download_files(urls)

# Clean up
app.close()
```

### Advanced Usage

```python
from Core.application import ApplicationFactory
from Core.config_manager import IniConfigManager

# Custom configuration
config = IniConfigManager('./custom/config.ini', './custom/mapping.json')
app = ApplicationFactory.create_custom_app(config)

# Get available download hosts
supported_hosts = app.get_supported_hosts()
print(f"Supported hosts: {supported_hosts}")

# Access individual components
scraper = app.get_scraper()
downloader = app.get_downloader()

# Detailed scraping with options
links = scraper.get_links(
    'http://example.com',
    id_name='content',
    element_type='a',
    attribute_={'href': re.compile(r'.*\.pdf$')}
)
```

## 🏗️ Architecture

### Modern Design Principles

The application follows clean architecture principles with dependency injection:

```
Core/
├── application.py          # Application factory and main orchestrator
├── config_manager.py       # Configuration management interface
├── http_client.py          # HTTP operations abstraction
├── file_manager.py         # File I/O operations
├── scraper.py             # Web scraping logic
├── download_orchestrator.py # Download coordination
├── download_strategy.py    # Strategy pattern for different hosts
└── exceptions.py          # Structured exception hierarchy
```

### Key Components

- **ApplicationFactory**: Creates configured applications for different environments
- **ConfigManager**: Handles configuration loading and validation
- **HttpClient**: Abstracts HTTP operations with mock support for testing
- **FileManager**: Manages file operations with progress tracking
- **StrategyRegistry**: Dynamic strategy resolution for different download hosts
- **DownloadOrchestrator**: Coordinates the entire download workflow

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest Tests/ -v

# Run only modern architecture tests
python -m pytest Tests/test_modern_scraper.py -v

# Test the architecture
python test_architecture.py
```

### Test Features

- **Mock HTTP Responses**: Test without network calls
- **Isolated Configuration**: Each test runs with clean configuration
- **Fast Execution**: Complete test suite runs in <1 second
- **Comprehensive Coverage**: 17/17 tests passing with full mock support

## ⚙️ Configuration

### Configuration Files

1. **Configuration/config.ini**: Main application settings
```ini
[Values]
user-agent={'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...'}

[Filenames]
download-folder=Books
scraped-links=links-scraped.txt

[Logging]
level=DEBUG
main-log=scraper-log
```

2. **Configuration/expression-mapping.json**: Download strategy mapping
```json
{
  "Download URL": {
    "drive.google.com": {
      "action": "process",
      "URL": "https://drive.google.com/uc",
      "File ID regex": "(?:id=|file/d/)(?P<id>[a-zA-Z0-9._-]*)",
      "Request Params": {"export": "download"},
      "Cookie": "download_warning"
    }
  }
}
```

### Adding New Download Hosts

1. Add URL pattern to `expression-mapping.json`
2. Create strategy class implementing `DownloadStrategy`
3. Register with `StrategyRegistry` via `StrategyFactory`

## 🛠️ Development

### Architecture Migration

The project supports both legacy and modern architecture:

- **Legacy**: Direct imports from `Core.scraper` and `Core.downloader`
- **Modern**: Use `ApplicationFactory` for dependency injection

### Contributing

1. Follow the dependency injection patterns
2. Add comprehensive tests for new features
3. Update configuration files for new download strategies
4. Maintain backward compatibility

## 📋 Requirements

- **Python 3.9+**
- **beautifulsoup4**: HTML/XML parsing
- **requests**: HTTP operations
- **clint**: Progress bar display
- **ddt**: Data-driven testing
- **lxml**: XML parsing support

## 📄 License

This project is available under the MIT License. See LICENSE file for details.

## 🔗 Links

- **GitHub**: [hasanrashid/Scraper](https://github.com/hasanrashid/Scraper)
- **Issues**: [Report bugs or request features](https://github.com/hasanrashid/Scraper/issues)
- **Documentation**: See `.github/copilot-instructions.md` for AI coding assistance

---

**Note**: This project has been modernized with dependency injection and clean architecture principles. Legacy code remains for backward compatibility.
