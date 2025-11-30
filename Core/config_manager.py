from abc import ABC, abstractmethod
from typing import Dict, List, Any
import logging
import configparser
import json
import os
from pathlib import Path
import datetime


class ConfigManager(ABC):
    """Abstract interface for configuration management"""
    
    @abstractmethod
    def get_user_agent(self) -> str:
        """Get the user agent string for HTTP requests"""
        pass
    
    @abstractmethod
    def get_download_folder(self) -> str:
        """Get the download folder path"""
        pass
    
    @abstractmethod
    def get_scraped_links_file(self) -> str:
        """Get the scraped links log file path"""
        pass
    
    @abstractmethod
    def get_download_errors_file(self) -> str:
        """Get the download errors log file path"""
        pass
    
    @abstractmethod
    def get_expression_mapping(self) -> Dict[str, Any]:
        """Get the URL expression mapping configuration"""
        pass
    
    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Get the list of supported file extensions"""
        pass
    
    @abstractmethod
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        pass


class IniConfigManager(ConfigManager):
    """Configuration manager that loads from INI and JSON files"""
    
    def __init__(self, ini_path: str = "./Configuration/config.ini", 
                 json_path: str = "./Configuration/expression-mapping.json"):
        self._load_configuration(ini_path, json_path)
        self._setup_logging()
        self._ensure_directories()
    
    def _load_configuration(self, ini_path: str, json_path: str):
        """Load configuration from files"""
        # Load INI configuration
        self.ini_config = configparser.ConfigParser()
        if not os.path.exists(ini_path):
            raise FileNotFoundError(f"Configuration file not found: {ini_path}")
        self.ini_config.read(ini_path)
        
        # Load JSON configuration
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Expression mapping file not found: {json_path}")
        with open(json_path, "r") as f:
            self.json_config = json.load(f)
        
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate required configuration fields"""
        required_ini_sections = ['Values', 'Filenames', 'Logging']
        for section in required_ini_sections:
            if not self.ini_config.has_section(section):
                raise ValueError(f"Missing required configuration section: {section}")
        
        required_fields = {
            ('Values', 'user-agent'),
            ('Filenames', 'download-folder'),
            ('Filenames', 'scraped-links'),
            ('Filenames', 'download-errors'),
            ('Logging', 'main-logger')
        }
        
        for section, key in required_fields:
            if not self.ini_config.has_option(section, key):
                raise ValueError(f"Missing required configuration: [{section}] {key}")
        
        if not self.json_config.get("Download URL"):
            raise ValueError("Missing Download URL configuration in expression mapping")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logs_dir = self.ini_config['Logging']['logs-folder']
        os.makedirs(logs_dir, exist_ok=True)
        
        log_filename = os.path.join(
            logs_dir,
            self.ini_config['Logging']['main-log'] + ' ' + 
            datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
        )
        
        logging.basicConfig(
            level=self.ini_config['Logging']['level'],
            format=self.ini_config['Logging']['formatter'],
            datefmt=self.ini_config['Logging']['date-format'],
            filename=log_filename,
            filemode='w'
        )
        
        self.logger = logging.getLogger(self.ini_config['Logging']['main-logger'])
    
    def _ensure_directories(self):
        """Create necessary directories"""
        download_folder_path = os.path.join(os.getcwd(), self.get_download_folder())
        os.makedirs(download_folder_path, exist_ok=True)
    
    def get_user_agent(self) -> str:
        return self.ini_config['Values']['user-agent']
    
    def get_download_folder(self) -> str:
        return self.ini_config['Filenames']['download-folder']
    
    def get_scraped_links_file(self) -> str:
        return self.ini_config['Filenames']['scraped-links']
    
    def get_download_errors_file(self) -> str:
        return self.ini_config['Filenames']['download-errors']
    
    def get_expression_mapping(self) -> Dict[str, Any]:
        return self.json_config
    
    def get_file_extensions(self) -> List[str]:
        return self.json_config.get('File Extensions', [])
    
    def get_logger(self) -> logging.Logger:
        return self.logger


class TestConfigManager(ConfigManager):
    """Configuration manager for testing purposes"""
    
    def __init__(self):
        self.test_config = {
            'user-agent': 'Mozilla/5.0 (Test) TestAgent/1.0',
            'download-folder': '/tmp/test-downloads',
            'scraped-links': '/tmp/test-scraped-links.txt',
            'download-errors': '/tmp/test-errors.txt',
            'file-extensions': ['pdf', 'rar'],
            'expression-mapping': {
                'Download URL': {
                    'test.com': {
                        'action': 'download'
                    }
                },
                'File Extensions': ['pdf', 'rar']
            }
        }
        
        # Setup basic logging for tests
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('TestLogger')
        
        # Ensure test directories exist
        os.makedirs('/tmp/test-downloads', exist_ok=True)
    
    def get_user_agent(self) -> str:
        return self.test_config['user-agent']
    
    def get_download_folder(self) -> str:
        return self.test_config['download-folder']
    
    def get_scraped_links_file(self) -> str:
        return self.test_config['scraped-links']
    
    def get_download_errors_file(self) -> str:
        return self.test_config['download-errors']
    
    def get_expression_mapping(self) -> Dict[str, Any]:
        return self.test_config['expression-mapping']
    
    def get_file_extensions(self) -> List[str]:
        return self.test_config['file-extensions']
    
    def get_logger(self) -> logging.Logger:
        return self.logger