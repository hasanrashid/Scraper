from typing import Optional, Tuple, List
import re
import datetime
import logging
import os
from Core.config_manager import ConfigManager
from Core.http_client import HttpClient
from Core.file_manager import FileManager
from Core.download_strategy import StrategyRegistry, StrategyFactory
from Core.exceptions import UnsupportedUrlError, DownloadError, FileProcessingError


class DownloadOrchestrator:
    """
    Orchestrates the download process using injected dependencies
    """
    
    def __init__(self, config_manager: ConfigManager, 
                 http_client: HttpClient, 
                 file_manager: FileManager,
                 strategy_registry: Optional[StrategyRegistry] = None):
        
        self.config = config_manager
        self.http_client = http_client
        self.file_manager = file_manager
        self.logger = config_manager.get_logger()
        
        # Initialize strategy registry if not provided
        if strategy_registry is None:
            # Note: We'll need to pass scraper instance for MediaFire
            self.strategy_registry = StrategyFactory.create_registry_from_config(
                self.config.get_expression_mapping(),
                self.http_client,
                scraper=None  # Will be injected later
            )
        else:
            self.strategy_registry = strategy_registry
    
    def set_scraper(self, scraper):
        """Set scraper instance for strategies that need it (like MediaFire)"""
        # Re-create registry with scraper
        self.strategy_registry = StrategyFactory.create_registry_from_config(
            self.config.get_expression_mapping(),
            self.http_client,
            scraper=scraper
        )
    
    def download_file(self, file_url: str, book_title: Optional[str] = None) -> Optional[Tuple[str, int]]:
        """
        Download a file from the given URL
        
        Args:
            file_url: URL to download from
            book_title: Optional custom filename
            
        Returns:
            Tuple of (filename, size) if successful, None if failed
        """
        
        try:
            # Validate URL format
            if not self._is_valid_url(file_url):
                raise DownloadError(file_url, "Invalid URL format")
            
            # Get appropriate download strategy
            strategy = self.strategy_registry.get_strategy(file_url)
            if not strategy:
                available_hosts = [s.get_host_name() for s in self.strategy_registry.get_all_strategies()]
                raise UnsupportedUrlError(file_url, available_hosts)
            
            self.logger.info(f"Using {strategy.__class__.__name__} for {file_url}")
            
            # Execute download strategy
            response = strategy.prepare_download(file_url)
            
            # Extract filename from response headers or use provided title
            filename = self._extract_filename(response, book_title, file_url)
            
            # Check if file already exists
            if self.file_manager.file_exists(filename):
                self.logger.info(f"File {filename} already exists, skipping download")
                return None
            
            # Save the file
            total_size = self._get_content_length(response)
            saved_filename, size = self.file_manager.save_file(
                filename, 
                response.iter_content(chunk_size=1024),
                total_size
            )
            
            # Log successful download
            size_mb = size / (1024 * 1024)
            self.file_manager.log_scraped_link(saved_filename, size_mb)
            
            self.logger.info(f"Successfully downloaded {saved_filename} ({size_mb:.2f} MB)")
            return (saved_filename, size)
            
        except Exception as e:
            error_msg = f"Download failed for {file_url}: {str(e)}"
            self.logger.error(error_msg)
            
            # Log error to error file
            self._log_download_error(file_url, str(e))
            
            return None
    
    def download_multiple_files(self, file_urls: List[str]) -> List[Tuple[str, int]]:
        """
        Download multiple files
        
        Args:
            file_urls: List of URLs to download
            
        Returns:
            List of successfully downloaded (filename, size) tuples
        """
        
        successful_downloads = []
        
        for url in file_urls:
            try:
                result = self.download_file(url)
                if result:
                    successful_downloads.append(result)
            except Exception as e:
                self.logger.error(f"Failed to download {url}: {str(e)}")
                continue
        
        return successful_downloads
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        expression_mapping = self.config.get_expression_mapping()
        download_link_regex = expression_mapping.get('Download Link RegEx')
        
        if download_link_regex:
            return bool(re.search(download_link_regex, url))
        
        # Basic URL validation fallback
        return url.startswith(('http://', 'https://'))
    
    def _extract_filename(self, response, book_title: Optional[str], url: str) -> str:
        """Extract filename from response headers or generate one"""
        
        if book_title:
            return book_title
        
        # Try to extract from Content-Disposition header
        if 'content-disposition' in response.headers:
            try:
                disposition = response.headers['content-disposition']
                filename_matches = re.findall('filename="(.+)"', disposition)
                if filename_matches:
                    return filename_matches[0]
            except Exception:
                pass
        
        # Try to extract from URL
        try:
            filename = os.path.basename(url.split('?')[0])  # Remove query parameters
            if filename and '.' in filename:
                return filename
        except Exception:
            pass
        
        # Generate default filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Try to determine extension from Content-Type
        extension = 'pdf'  # Default
        if 'content-type' in response.headers:
            content_type = response.headers['content-type']
            if 'pdf' in content_type:
                extension = 'pdf'
            elif 'zip' in content_type or 'rar' in content_type:
                extension = 'zip'
        
        return f"download_{timestamp}.{extension}"
    
    def _get_content_length(self, response) -> Optional[int]:
        """Get content length from response headers"""
        try:
            return int(response.headers.get('content-length', 0))
        except (ValueError, TypeError):
            return None
    
    def _log_download_error(self, url: str, error: str):
        """Log download error to error file"""
        try:
            error_file = self.config.get_download_errors_file()
            with open(error_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"\n[{timestamp}] Error downloading: {url} - {error}\n")
        except Exception as e:
            self.logger.error(f"Failed to log download error: {str(e)}")
    
    def get_supported_hosts(self) -> List[str]:
        """Get list of supported host names"""
        return [strategy.get_host_name() for strategy in self.strategy_registry.get_all_strategies()]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up HTTP client if needed
        if hasattr(self.http_client, 'close'):
            self.http_client.close()