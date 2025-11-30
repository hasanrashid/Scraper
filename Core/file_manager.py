from abc import ABC, abstractmethod
from typing import Optional, Tuple
import os
import logging
from clint.textui import progress


class FileManager(ABC):
    """Abstract interface for file operations"""
    
    @abstractmethod
    def file_exists(self, filename: str) -> bool:
        """Check if file exists in download directory"""
        pass
    
    @abstractmethod
    def save_file(self, filename: str, content_iterator, 
                  total_size: Optional[int] = None) -> Tuple[str, int]:
        """Save file with progress tracking"""
        pass
    
    @abstractmethod
    def log_scraped_link(self, filename: str, size_mb: float):
        """Log successful download to scraped links file"""
        pass


class FileSystemManager(FileManager):
    """File manager implementation using local file system"""
    
    def __init__(self, download_folder: str, scraped_links_file: str, logger: logging.Logger):
        self.download_folder = download_folder
        self.scraped_links_file = scraped_links_file
        self.logger = logger
        
        # Ensure download directory exists
        self._ensure_download_directory()
    
    def _ensure_download_directory(self):
        """Create download directory if it doesn't exist"""
        full_path = os.path.join(os.getcwd(), self.download_folder)
        os.makedirs(full_path, exist_ok=True)
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists in download directory"""
        file_path = os.path.join(os.getcwd(), self.download_folder, filename)
        return os.path.isfile(file_path)
    
    def save_file(self, filename: str, content_iterator, 
                  total_size: Optional[int] = None) -> Tuple[str, int]:
        """Save file with progress tracking"""
        
        file_path = os.path.join(os.getcwd(), self.download_folder, filename)
        
        try:
            with open(file_path, 'wb') as file:
                size = 0
                
                if total_size:
                    # Use progress bar if total size is known
                    progress_bar = progress.bar(
                        content_iterator, 
                        expected_size=(total_size / 1024) + 1
                    )
                    
                    for chunk in progress_bar:
                        if chunk:
                            file.write(chunk)
                            file.flush()
                            size += len(chunk)
                else:
                    # Save without progress bar
                    for chunk in content_iterator:
                        if chunk:
                            file.write(chunk)
                            file.flush()
                            size += len(chunk)
                
                self.logger.info(f"Successfully saved {filename} ({size} bytes)")
                return filename, size
                
        except Exception as e:
            self.logger.error(f"Failed to save file {filename}: {str(e)}")
            # Clean up partial file
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
    
    def log_scraped_link(self, filename: str, size_mb: float):
        """Log successful download to scraped links file"""
        try:
            with open(self.scraped_links_file, 'a+', encoding='utf-8') as f:
                f.write(f"\n{filename}: {size_mb:.2f} Megabytes\n")
        except Exception as e:
            self.logger.error(f"Failed to log scraped link: {str(e)}")


class MockFileManager(FileManager):
    """Mock file manager for testing"""
    
    def __init__(self):
        self.saved_files = {}  # filename -> (content, size)
        self.scraped_links_log = []
        self.existing_files = set()
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists in mock storage"""
        return filename in self.existing_files
    
    def save_file(self, filename: str, content_iterator, 
                  total_size: Optional[int] = None) -> Tuple[str, int]:
        """Save file to mock storage"""
        content = b''.join(content_iterator)
        size = len(content)
        
        self.saved_files[filename] = (content, size)
        self.existing_files.add(filename)
        
        return filename, size
    
    def log_scraped_link(self, filename: str, size_mb: float):
        """Log scraped link to mock log"""
        self.scraped_links_log.append((filename, size_mb))
    
    def add_existing_file(self, filename: str):
        """Add file to existing files set for testing"""
        self.existing_files.add(filename)
    
    def get_saved_content(self, filename: str) -> Optional[bytes]:
        """Get saved file content for testing"""
        if filename in self.saved_files:
            return self.saved_files[filename][0]
        return None
    
    def get_scraped_links_log(self):
        """Get logged scraped links for testing"""
        return self.scraped_links_log