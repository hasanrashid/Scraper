from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import re
import requests
from Core.http_client import HttpClient


class DownloadStrategy(ABC):
    """Abstract interface for download strategies"""
    
    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """Check if this strategy can handle the given URL"""
        pass
    
    @abstractmethod
    def prepare_download(self, url: str) -> requests.Response:
        """Prepare and execute download, returning response stream"""
        pass
    
    @abstractmethod
    def get_host_name(self) -> str:
        """Get the host name this strategy handles"""
        pass


class BaseDownloadStrategy(DownloadStrategy):
    """Base implementation with common functionality"""
    
    def __init__(self, http_client: HttpClient, config: Dict[str, Any]):
        self.http_client = http_client
        self.config = config
    
    def extract_file_id(self, url: str) -> Dict[str, str]:
        """Extract file ID using regex from config"""
        if 'File ID regex' not in self.config:
            return {}
        
        regex_pattern = self.config['File ID regex']
        match = re.search(regex_pattern, url)
        
        if not match:
            raise ValueError(f"Could not extract file ID from {url} using pattern {regex_pattern}")
        
        return match.groupdict()


class DirectDownloadStrategy(BaseDownloadStrategy):
    """Strategy for direct downloads (no processing required)"""
    
    def __init__(self, http_client: HttpClient, host_name: str):
        super().__init__(http_client, {'action': 'download'})
        self.host_name = host_name
    
    def supports_url(self, url: str) -> bool:
        return self.host_name in url
    
    def prepare_download(self, url: str) -> requests.Response:
        return self.http_client.get(url, stream=True)
    
    def get_host_name(self) -> str:
        return self.host_name


class GoogleDriveStrategy(BaseDownloadStrategy):
    """Strategy for Google Drive downloads"""
    
    def __init__(self, http_client: HttpClient, config: Dict[str, Any]):
        super().__init__(http_client, config)
    
    def supports_url(self, url: str) -> bool:
        return 'drive.google.com' in url
    
    def prepare_download(self, url: str) -> requests.Response:
        # Extract file ID
        file_params = self.extract_file_id(url)
        
        # Prepare request parameters
        params = file_params.copy()
        params.update(self.config.get('Request Params', {}))
        
        # First request to get download cookie
        response = self.http_client.get(self.config['URL'], params=params)
        
        # Look for download warning cookie
        cookie_name = self.config.get('Cookie')
        if cookie_name:
            for cookie, value in response.cookies.items():
                if cookie_name in cookie:
                    params['confirm'] = value
                    break
        
        # Final request with confirmation
        return self.http_client.get(self.config['URL'], params=params, stream=True)
    
    def get_host_name(self) -> str:
        return 'drive.google.com'


class DataFileHostStrategy(BaseDownloadStrategy):
    """Strategy for DataFileHost downloads"""
    
    def __init__(self, http_client: HttpClient, config: Dict[str, Any]):
        super().__init__(http_client, config)
    
    def supports_url(self, url: str) -> bool:
        return 'datafilehost.com' in url
    
    def prepare_download(self, url: str) -> requests.Response:
        # Extract file parameters
        file_params = self.extract_file_id(url)
        
        # Get session cookie from original URL
        response = self.http_client.get(url)
        
        # Extract session cookies
        cookies = {}
        cookie_name = self.config.get('Cookie')
        if cookie_name:
            for cookie, value in response.cookies.items():
                if cookie_name in cookie:
                    cookies[cookie] = value
                    break
        
        # Make request to download endpoint
        return self.http_client.get(
            self.config['URL'], 
            params=file_params, 
            cookies=cookies, 
            stream=True
        )
    
    def get_host_name(self) -> str:
        return 'www.datafilehost.com'


class MediaFireStrategy(BaseDownloadStrategy):
    """Strategy for MediaFire downloads"""
    
    def __init__(self, http_client: HttpClient, scraper):
        super().__init__(http_client, {'action': 'process'})
        self.scraper = scraper  # Need scraper to extract download link
    
    def supports_url(self, url: str) -> bool:
        return 'mediafire.com' in url
    
    def prepare_download(self, url: str) -> requests.Response:
        # Use scraper to extract download button URL
        download_links = self.scraper.get_links(
            url, 
            element_type='a', 
            id_name="downloadButton"
        )
        
        if not download_links:
            raise ValueError(f"Could not find download button for MediaFire URL: {url}")
        
        download_url = download_links[0]['href']
        return self.http_client.get(download_url, stream=True)
    
    def get_host_name(self) -> str:
        return 'www.mediafire.com'


class StrategyRegistry:
    """Registry for managing download strategies"""
    
    def __init__(self):
        self.strategies: List[DownloadStrategy] = []
    
    def register(self, strategy: DownloadStrategy):
        """Register a new download strategy"""
        self.strategies.append(strategy)
    
    def get_strategy(self, url: str) -> Optional[DownloadStrategy]:
        """Get appropriate strategy for URL"""
        for strategy in self.strategies:
            if strategy.supports_url(url):
                return strategy
        return None
    
    def get_all_strategies(self) -> List[DownloadStrategy]:
        """Get all registered strategies"""
        return self.strategies.copy()


class StrategyFactory:
    """Factory for creating strategies from configuration"""
    
    @staticmethod
    def create_from_config(host_name: str, host_config: Dict[str, Any], 
                          http_client: HttpClient, scraper=None) -> DownloadStrategy:
        """Create strategy instance from configuration"""
        
        action = host_config.get('action', 'download')
        
        if action == 'download':
            return DirectDownloadStrategy(http_client, host_name)
        elif host_name == 'drive.google.com':
            return GoogleDriveStrategy(http_client, host_config)
        elif host_name == 'www.datafilehost.com':
            return DataFileHostStrategy(http_client, host_config)
        elif 'mediafire.com' in host_name:
            if not scraper:
                raise ValueError("MediaFire strategy requires scraper instance")
            return MediaFireStrategy(http_client, scraper)
        else:
            raise ValueError(f"Unknown strategy configuration for host: {host_name}")
    
    @staticmethod
    def create_registry_from_config(expression_mapping: Dict[str, Any], 
                                   http_client: HttpClient, scraper=None) -> StrategyRegistry:
        """Create strategy registry from expression mapping configuration"""
        
        registry = StrategyRegistry()
        download_urls = expression_mapping.get('Download URL', {})
        
        for host_name, host_config in download_urls.items():
            try:
                strategy = StrategyFactory.create_from_config(
                    host_name, host_config, http_client, scraper
                )
                registry.register(strategy)
            except Exception as e:
                # Log warning but continue with other strategies
                print(f"Warning: Could not create strategy for {host_name}: {e}")
        
        return registry