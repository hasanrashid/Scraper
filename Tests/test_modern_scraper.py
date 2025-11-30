import unittest
from unittest.mock import Mock, patch
from ddt import ddt, data, unpack, file_data
import requests
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.application import ApplicationFactory
from Core.config_manager import TestConfigManager
from Core.http_client import MockHttpClient
from Core.exceptions import ScrapingError, HttpError
import logging, json
import re

@ddt
class ModernScrapeMethodTests(unittest.TestCase):
    """
    Updated tests using the new architecture with dependency injection
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test application with mock dependencies"""
        
        # Create mock HTTP responses
        mock_responses = {}
        
        # Create a mock response for the test URL
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <body>
                <div id="post-body-9192865501445967797">
                    <a href="http://example.com/file1.pdf">File 1</a>
                    <a href="http://example.com/file2.pdf">File 2</a>
                </div>
                <div class="post-body entry-content">
                    <a href="http://example.com/file3.pdf">File 3</a>
                </div>
                <a href="http://example.com/file4.pdf">File 4</a>
            </body>
        </html>
        '''
        
        mock_responses['http://banglaclassicbooks.blogspot.com/'] = mock_response
        
        # Create test application
        cls.app = ApplicationFactory.create_test_app(mock_responses)
        cls.scraper = cls.app.get_scraper()
        cls.url = 'http://banglaclassicbooks.blogspot.com/'
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test resources"""
        cls.app.close()

    @file_data("test_get_links.json")
    def test_get_links(self, id_name=None, class_name=None, element_type=None, element_attribute=None, css_selector=None):
        """Test link extraction with various parameters"""
        
        # Convert element_attribute to proper format if provided
        attr_ = None
        if element_attribute is not None:
            attr_ = {element_attribute['attribute']: re.compile(element_attribute['regex'])}
        
        # Test the scraper
        result = self.scraper.get_links(
            self.url, 
            id_name=id_name,
            class_name=class_name, 
            element_type=element_type, 
            attribute_=attr_, 
            css_selector=css_selector
        )
        
        # Should return some results
        self.assertIsNotNone(result)
        
        # Should be a list
        self.assertIsInstance(result, list)
    
    def test_get_links_with_invalid_url(self):
        """Test error handling for invalid URLs"""
        
        # Add mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        self.scraper.http_client.add_mock_response('http://invalid-url.com/', mock_response)
        
        # Should return None for invalid URL
        result = self.scraper.get_links('http://invalid-url.com/')
        self.assertIsNone(result)
    
    def test_get_links_with_network_error(self):
        """Test error handling for network errors"""
        
        # Mock HTTP client to raise exception
        original_get = self.scraper.http_client.get
        
        def mock_get_with_error(url, **kwargs):
            raise requests.exceptions.RequestException("Network error")
        
        self.scraper.http_client.get = mock_get_with_error
        
        try:
            result = self.scraper.get_links(self.url)
            self.assertIsNone(result)
        finally:
            # Restore original method
            self.scraper.http_client.get = original_get
    
    def test_scraper_configuration_injection(self):
        """Test that configuration is properly injected"""
        
        # Check that scraper has access to configuration
        self.assertIsNotNone(self.scraper.config)
        self.assertIsNotNone(self.scraper.logger)
        self.assertIsNotNone(self.scraper.http_client)
        
        # Check configuration values
        self.assertEqual(
            self.scraper.config.get_user_agent(),
            'Mozilla/5.0 (Test) TestAgent/1.0'
        )
    
    def test_http_client_integration(self):
        """Test HTTP client integration"""
        
        # Check that HTTP client is properly configured
        self.assertIsNotNone(self.scraper.http_client)
        
        # Check request logging (if using MockHttpClient)
        if hasattr(self.scraper.http_client, 'request_log'):
            initial_log_count = len(self.scraper.http_client.request_log)
            
            # Make a request
            self.scraper.get_links(self.url)
            
            # Should have logged the request
            self.assertGreater(len(self.scraper.http_client.request_log), initial_log_count)

if __name__ == '__main__':
    unittest.main()