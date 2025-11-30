"""
Application factory for creating configured scraper instances
"""

from Core.config_manager import ConfigManager, IniConfigManager, TestConfigManager
from Core.http_client import HttpClient, RequestsHttpClient, MockHttpClient
from Core.file_manager import FileManager, FileSystemManager, MockFileManager
from Core.download_orchestrator import DownloadOrchestrator
from Core.scraper import Scraper
from Core.download_strategy import StrategyRegistry, StrategyFactory


class ScraperApplication:
    """
    Main application class that wires together all components
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = config_manager.get_logger()
        
        # Initialize core components
        self.http_client = self._create_http_client()
        self.file_manager = self._create_file_manager()
        self.scraper = self._create_scraper()
        self.download_orchestrator = self._create_download_orchestrator()
        
        # Set up bidirectional dependencies
        self.download_orchestrator.set_scraper(self.scraper)
    
    def _create_http_client(self) -> HttpClient:
        """Create HTTP client with configured user agent"""
        return RequestsHttpClient(self.config.get_user_agent())
    
    def _create_file_manager(self) -> FileManager:
        """Create file manager with configured paths"""
        return FileSystemManager(
            self.config.get_download_folder(),
            self.config.get_scraped_links_file(),
            self.logger
        )
    
    def _create_scraper(self) -> Scraper:
        """Create scraper with configured dependencies"""
        return Scraper(self.config, self.http_client)
    
    def _create_download_orchestrator(self) -> DownloadOrchestrator:
        """Create download orchestrator with all dependencies"""
        return DownloadOrchestrator(
            self.config,
            self.http_client,
            self.file_manager
        )
    
    def get_scraper(self) -> Scraper:
        """Get the configured scraper instance"""
        return self.scraper
    
    def get_downloader(self) -> DownloadOrchestrator:
        """Get the configured download orchestrator"""
        return self.download_orchestrator
    
    def get_supported_hosts(self) -> list:
        """Get list of supported download hosts"""
        return self.download_orchestrator.get_supported_hosts()
    
    def scrape_links(self, url: str, **kwargs):
        """Convenience method for scraping links"""
        return self.scraper.get_links(url, **kwargs)
    
    def download_file(self, url: str, filename: str = None):
        """Convenience method for downloading a file"""
        return self.download_orchestrator.download_file(url, filename)
    
    def download_files(self, urls: list):
        """Convenience method for downloading multiple files"""
        return self.download_orchestrator.download_multiple_files(urls)
    
    def close(self):
        """Clean up resources"""
        if hasattr(self.http_client, 'close'):
            self.http_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ApplicationFactory:
    """
    Factory for creating different application configurations
    """
    
    @staticmethod
    def create_production_app(ini_path: str = None, json_path: str = None) -> ScraperApplication:
        """
        Create production application with file-based configuration
        
        Args:
            ini_path: Path to INI configuration file
            json_path: Path to JSON expression mapping file
            
        Returns:
            Configured ScraperApplication instance
        """
        
        # Use default paths if not specified
        ini_path = ini_path or "./Configuration/config.ini"
        json_path = json_path or "./Configuration/expression-mapping.json"
        
        config_manager = IniConfigManager(ini_path, json_path)
        return ScraperApplication(config_manager)
    
    @staticmethod
    def create_test_app(mock_http_responses=None) -> ScraperApplication:
        """
        Create test application with mock dependencies
        
        Args:
            mock_http_responses: Dictionary of URL -> Response mappings for testing
            
        Returns:
            Test-configured ScraperApplication instance
        """
        
        config_manager = TestConfigManager()
        app = ScraperApplication(config_manager)
        
        # Replace HTTP client with mock for testing
        if mock_http_responses:
            from Core.http_client import MockHttpClient
            app.http_client = MockHttpClient(mock_http_responses)
            
            # Replace file manager with mock
            from Core.file_manager import MockFileManager
            app.file_manager = MockFileManager()
            
            # Recreate dependent components
            app.scraper = Scraper(config_manager, app.http_client)
            app.download_orchestrator = DownloadOrchestrator(
                config_manager,
                app.http_client,
                app.file_manager
            )
            app.download_orchestrator.set_scraper(app.scraper)
        
        return app
    
    @staticmethod
    def create_custom_app(config_manager: ConfigManager,
                         http_client: HttpClient = None,
                         file_manager: FileManager = None) -> ScraperApplication:
        """
        Create application with custom dependencies
        
        Args:
            config_manager: Custom configuration manager
            http_client: Custom HTTP client (optional)
            file_manager: Custom file manager (optional)
            
        Returns:
            Custom-configured ScraperApplication instance
        """
        
        app = ScraperApplication(config_manager)
        
        if http_client:
            app.http_client = http_client
            app.scraper = Scraper(config_manager, http_client)
            app.download_orchestrator = DownloadOrchestrator(
                config_manager, http_client, app.file_manager
            )
            app.download_orchestrator.set_scraper(app.scraper)
        
        if file_manager:
            app.file_manager = file_manager
            app.download_orchestrator = DownloadOrchestrator(
                config_manager, app.http_client, file_manager
            )
            app.download_orchestrator.set_scraper(app.scraper)
        
        return app


# Convenience function for quick setup
def create_scraper_app(config_path: str = None) -> ScraperApplication:
    """
    Quick setup function for creating a production scraper application
    
    Args:
        config_path: Optional path to configuration directory
        
    Returns:
        Ready-to-use ScraperApplication instance
    """
    
    if config_path:
        ini_path = f"{config_path}/config.ini"
        json_path = f"{config_path}/expression-mapping.json"
        return ApplicationFactory.create_production_app(ini_path, json_path)
    else:
        return ApplicationFactory.create_production_app()