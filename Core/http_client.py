from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Tuple
import requests
import time


class HttpClient(ABC):
    """Abstract interface for HTTP operations"""
    
    @abstractmethod
    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            cookies: Optional[Dict[str, str]] = None, 
            stream: bool = False) -> requests.Response:
        """Execute HTTP GET request"""
        pass


class RequestsHttpClient(HttpClient):
    """HTTP client implementation using requests library with timeout and retry support"""
    
    def __init__(self, user_agent: str, timeout: Tuple[int, int] = (10, 60), 
                 max_retries: int = 3, retry_backoff_seconds: int = 5):
        self.session = requests.Session()
        self.headers = {'user-agent': user_agent}
        self.timeout = timeout  # (connect timeout, read timeout)
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            cookies: Optional[Dict[str, str]] = None, 
            stream: bool = False) -> requests.Response:
        """Execute HTTP GET request with timeout and retry logic"""
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url, 
                    headers=self.headers,
                    params=params,
                    cookies=cookies,
                    stream=stream,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response
                
                # Retry on server errors
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt < self.max_retries:
                        time.sleep(self.retry_backoff_seconds)
                        continue
                    
                    raise requests.exceptions.HTTPError(
                        f"Request returned status code {response.status_code} after {self.max_retries} attempts"
                    )
                
                # Don't retry on client errors (except 429)
                raise requests.exceptions.HTTPError(
                    f"Request returned status code {response.status_code}"
                )
            
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds)
                    continue
                # Will raise after loop
                break
        
        # If we got here, all retries failed
        if last_error:
            raise last_error
        
        raise requests.exceptions.RequestException(
            f"Request failed after {self.max_retries} attempts"
        )
    
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