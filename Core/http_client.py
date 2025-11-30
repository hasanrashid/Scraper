from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import requests


class HttpClient(ABC):
    """Abstract interface for HTTP operations"""
    
    @abstractmethod
    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            cookies: Optional[Dict[str, str]] = None, 
            stream: bool = False) -> requests.Response:
        """Execute HTTP GET request"""
        pass


class RequestsHttpClient(HttpClient):
    """HTTP client implementation using requests library"""
    
    def __init__(self, user_agent: str):
        self.session = requests.Session()
        self.headers = {'user-agent': user_agent}
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            cookies: Optional[Dict[str, str]] = None, 
            stream: bool = False) -> requests.Response:
        """Execute HTTP GET request with error handling"""
        
        response = self.session.get(
            url, 
            headers=self.headers,
            params=params,
            cookies=cookies,
            stream=stream
        )
        
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(
                f"Request returned status code {response.status_code}"
            )
        
        return response
    
    def close(self):
        """Close the HTTP session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MockHttpClient(HttpClient):
    """Mock HTTP client for testing"""
    
    def __init__(self, mock_responses: Optional[Dict[str, requests.Response]] = None):
        self.mock_responses = mock_responses or {}
        self.request_log = []  # Track requests for testing
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            cookies: Optional[Dict[str, str]] = None, 
            stream: bool = False) -> requests.Response:
        """Return mock response or raise exception"""
        
        # Log the request
        self.request_log.append({
            'url': url,
            'params': params,
            'cookies': cookies,
            'stream': stream
        })
        
        if url in self.mock_responses:
            return self.mock_responses[url]
        
        # Return default 404 response
        response = requests.Response()
        response.status_code = 404
        return response
    
    def add_mock_response(self, url: str, response: requests.Response):
        """Add a mock response for a specific URL"""
        self.mock_responses[url] = response
    
    def get_request_log(self):
        """Get log of all requests made"""
        return self.request_log