"""
Custom exception hierarchy for the scraper application
"""


class ScraperError(Exception):
    """Base exception class for all scraper-related errors"""
    pass


class ConfigurationError(ScraperError):
    """Raised when there are configuration-related issues"""
    pass


class UnsupportedUrlError(ScraperError):
    """Raised when a URL is not supported by any available strategy"""
    
    def __init__(self, url: str, available_hosts: list = None):
        self.url = url
        self.available_hosts = available_hosts or []
        
        if self.available_hosts:
            message = (f"URL '{url}' is not supported. "
                      f"Supported hosts: {', '.join(self.available_hosts)}")
        else:
            message = f"URL '{url}' is not supported by any available strategy"
        
        super().__init__(message)


class DownloadError(ScraperError):
    """Raised when file download fails"""
    
    def __init__(self, url: str, reason: str = None):
        self.url = url
        self.reason = reason
        
        message = f"Failed to download from '{url}'"
        if reason:
            message += f": {reason}"
        
        super().__init__(message)


class FileProcessingError(ScraperError):
    """Raised when file processing operations fail"""
    
    def __init__(self, filename: str, operation: str, reason: str = None):
        self.filename = filename
        self.operation = operation
        self.reason = reason
        
        message = f"Failed to {operation} file '{filename}'"
        if reason:
            message += f": {reason}"
        
        super().__init__(message)


class ScrapingError(ScraperError):
    """Raised when web scraping operations fail"""
    
    def __init__(self, url: str, reason: str = None):
        self.url = url
        self.reason = reason
        
        message = f"Failed to scrape '{url}'"
        if reason:
            message += f": {reason}"
        
        super().__init__(message)


class HttpError(ScraperError):
    """Raised when HTTP operations fail"""
    
    def __init__(self, url: str, status_code: int = None, reason: str = None):
        self.url = url
        self.status_code = status_code
        self.reason = reason
        
        message = f"HTTP error for '{url}'"
        if status_code:
            message += f" (status: {status_code})"
        if reason:
            message += f": {reason}"
        
        super().__init__(message)


class StrategyError(ScraperError):
    """Raised when strategy execution fails"""
    
    def __init__(self, strategy_name: str, url: str, reason: str = None):
        self.strategy_name = strategy_name
        self.url = url
        self.reason = reason
        
        message = f"Strategy '{strategy_name}' failed for URL '{url}'"
        if reason:
            message += f": {reason}"
        
        super().__init__(message)