import itertools
from typing import Optional, List, Dict, Any, Union
from bs4 import BeautifulSoup, SoupStrainer, Tag
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime
from Core.config_manager import ConfigManager
from Core.http_client import HttpClient
from Core.exceptions import ScrapingError, HttpError
#from Core.downloader import Downloader
import inspect

class Scraper:
    def __init__(self, config_manager: ConfigManager, http_client: Optional[HttpClient] = None) -> None:
        self.config = config_manager
        self.logger = config_manager.get_logger()
        
        # Use provided HTTP client or create default one
        if http_client:
            self.http_client = http_client
        else:
            from Core.http_client import RequestsHttpClient
            self.http_client = RequestsHttpClient(config_manager.get_user_agent())

    '''
    Method is given a url, optinal id and/or class name and an element type that defaults to an
    HTML anchor.
    '''
    def get_links(self, url: str, id_name: Optional[str] = None, class_name: Optional[str] = None, 
                  element_type: Optional[str] = None, attribute_: Optional[Dict[str, Any]] = None, 
                  css_selector: Optional[str] = None, features: Optional[str] = None, 
                  links_only: bool = True) -> Optional[List[Tag]]:
        """
        Extract links from a webpage using various selection methods
        
        Args:
            url: URL to scrape
            id_name: HTML element ID to target
            class_name: CSS class name to target
            element_type: HTML element type (default: 'a')
            attribute_: Attribute dictionary for selection
            css_selector: CSS selector string
            features: Parser features ('xml' for XML parsing)
            links_only: Whether to return only anchor tags
            
        Returns:
            List of BeautifulSoup Tag objects or None if failed
        """
        
        try:
            self.logger.info(f'Starting scraping for URL: {url}')
            
            # Make HTTP request
            response = self.http_client.get(url)
            
            if response.status_code != 200:
                raise HttpError(url, response.status_code, "Request failed")
            
            # Parse response
            links = self._parse_response(response, id_name, class_name, element_type, 
                                       attribute_, css_selector, features, links_only)
            
            self.logger.info(f'Successfully extracted {len(links) if links else 0} links from {url}')
            return links
            
        except Exception as e:
            error_msg = f"Error processing URL {url}: {str(e)}"
            self.logger.error(error_msg)
            
            # Log error to file
            self._log_scraping_error(url, str(e))
            
            return None
    
    def _parse_response(self, response: requests.Response, id_name: Optional[str] = None, 
                      class_name: Optional[str] = None, element_type: Optional[str] = None,
                      attribute_: Optional[Dict[str, Any]] = None, 
                      css_selector: Optional[str] = None, features: Optional[str] = None,
                      links_only: bool = True) -> Optional[List[Tag]]:
        """
        Parse HTTP response and extract elements based on provided criteria
        """
        
        null_values = ['', None]
        
        # Validate input parameters
        if (all(x not in null_values for x in [id_name, class_name])):
            warnings.warn('Both css id and class was provided. class will be ignored')
        
        # Set up parsing strategy
        if id_name is not None:
            soup_strainer = SoupStrainer(element_type, id=id_name)
        elif class_name is not None:
            soup_strainer = SoupStrainer(element_type, class_=class_name)
        else:
            soup_strainer = SoupStrainer(element_type)
        
        # Choose parser
        if features == 'xml':
            soup = BeautifulSoup(response.content, 'xml', parse_only=soup_strainer)
        else:
            soup = BeautifulSoup(response.content, 'html.parser', parse_only=soup_strainer)
        
        # Extract elements based on criteria
        if attribute_ not in null_values:
            links = soup.find_all(attrs=attribute_)
        elif css_selector not in null_values:
            links = soup.select(css_selector)
        else:
            if features == 'xml':
                links = soup.find_all('loc')
            else:
                if links_only:
                    links = soup.find_all('a')
                else:
                    links = soup.find_all()
        
        return links
    
    def _log_scraping_error(self, url: str, error: str):
        """Log scraping error to error file"""
        try:
            error_file = self.config.get_download_errors_file()
            with open(error_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"\n[{timestamp}] Scraping error for {url}: {error}\n")
        except Exception as e:
            self.logger.error(f"Failed to log scraping error: {str(e)}")

