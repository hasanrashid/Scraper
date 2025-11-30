# Scraper Project - AI Coding Assistant Guide

This is a Python web scraping application designed to extract and download PDF documents from websites using configurable strategies for different file hosting services.

## Architecture Overview

The project follows a modular OOP design with four core components:

- **Core/scraper.py**: Main scraping logic using BeautifulSoup with SoupStrainer for memory efficiency
- **Core/downloader.py**: Download orchestration with host-specific strategies via decorator pattern
- **Core/download_strategies.py**: Host-specific download implementations (Google Drive, MediaFire, DataFileHost, etc.)
- **Core/decorator.py**: Strategy pattern decorator that routes downloads based on URL patterns
- **Configuration/**: Centralized config management using INI files and JSON expression mappings

## Key Patterns & Conventions

### Configuration-Driven Architecture
- All settings live in `Configuration/config.ini` (file paths, logging, user-agent)
- URL patterns and host mappings defined in `Configuration/expression-mapping.json`
- Regex patterns for file ID extraction stored as JSON configuration, not hardcoded

### Strategy Pattern for Downloads
```python
# Host mapping in downloader.py __init__:
self.prepare_function = {
    'mega.nz': strategies.prepare_mega,
    'drive.google.com': strategies.prepare_google,
    'www.datafilehost.com': strategies.prepare_datafilehost,
    # ...
}
```

### Decorator Pattern for Request Processing
All download strategies use the `@response_decorator` which:
- Extracts host from URL using regex from config
- Validates host against known patterns
- Prepares request parameters from JSON config
- Handles file ID extraction automatically

### Error Handling & Logging
- Comprehensive logging configured via INI settings
- Error files tracked in `download_errors` config setting
- Custom `raise_exception()` function logs before raising
- Session management with proper context managers (`with` statements)

## Development Workflows

### Testing Data Format
Test files use JSON with descriptive keys and parameter objects:
```json
{
    "test_case_name": {
        "id_name": "post-body-123",
        "class_name": "content",
        "element_type": "a",
        "element_attribute": {
            "attribute": "href",
            "regex": ".*\\.pdf$"
        },
        "css_selector": ".download-link"
    }
}
```
The `@file_data("test_file.json")` decorator automatically unpacks these as test parameters.
```bash
python -m pytest Tests/
# Or specific test files
python -m pytest Tests/test_scraper.py
```

### Adding New Download Hosts
1. Add URL pattern to `Configuration/expression-mapping.json` under "Download URL":
```json
"new-host.com": {
    "action": "process",  // or "download" for direct downloads
    "URL": "https://new-host.com/api/download",
    "File ID regex": "\/file\/(?P<id>[a-zA-Z0-9]+)",  // named groups required
    "Request Params": {"format": "binary"},  // optional
    "Cookie": "session_id"  // cookie name to extract
}
```
2. Create new strategy function in `Core/download_strategies.py` with `@response_decorator`
3. Add mapping in `Downloader.__init__()` prepare_function dictionary: `'new-host.com': strategies.prepare_new_host`

### Configuration Changes
- **File paths**: Modify `Configuration/config.ini` [Filenames] section:
  ```ini
  [Filenames]
  scraped-links=links-boierpathshala.txt
  download-errors=download_error.txt
  download-folder=Books
  ```
- **Logging**: Adjust [Logging] section in config.ini with Windows-style paths:
  ```ini
  [Logging]
  logs-folder=Logs
  main-log=scraper-log
  test-log=unit-test-log
  date-format="%%m-%%d %%H:%%M"
  formatter=%%(asctime)s %%(name)-12s %%(levelname)-8s %%(filename)s %%(funcName)s %%(lineno)d %%(message)s
  main-logger=ScraperLog
  test-logger=TestLog
  level=DEBUG
  ```
  - Log files auto-append current date: `scraper-log 2025-11-30.log`
  - Formatter uses double `%%` for escaping in config files
  - Supports separate loggers for main app vs tests
  - Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **URL patterns**: Update `Configuration/expression-mapping.json` structure:
  ```json
  {
    "Download Link RegEx": "\/\/(?:download[0-9]*\\.|ia[0-9]*\\.)?(.*?)\/",
    "File Extensions": ["pdf", "rar"],
    "Download URL": {
      "host.com": {
        "action": "process|download",
        "URL": "api_endpoint",
        "File ID regex": "(?P<named_group>pattern)",
        "Request Params": {},
        "Cookie": "cookie_name"
      }
    }
  }
  ```

## Critical Integration Points

### BeautifulSoup Usage Pattern
Uses `SoupStrainer` for memory efficiency when parsing large pages:
```python
soup_strainer = SoupStrainer(element_type, id=id_name)
bs = BeautifulSoup(resp.content, 'html.parser', parse_only=soup_strainer)
```

### Session Management
- Persistent `requests.Session` objects in both Scraper and Downloader classes
- Always use `with` statements for file operations and responses
- Custom headers from config applied to all requests

### File System Structure
- Downloads go to configurable folder (config.ini: download-folder)
- Scraped links logged to configurable file (config.ini: scraped-links) 
- Existing file detection prevents re-downloads

## Common Gotchas

- **Windows path separators**: Logging config uses Windows-style backslashes in paths
- **Regex groupdict()**: Download strategies expect named capture groups in File ID regex patterns
- **Progress bars**: Uses both `clint.textui.progress` and `tqdm` - prefer `progress.bar()` for downloads
- **Content-Type detection**: File extensions extracted from HTTP headers, not URLs
- **Context managers**: All download strategies must work as context managers (implement `__enter__`/`__exit__`)