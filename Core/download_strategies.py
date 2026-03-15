import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime, tempfile
import urllib.parse
import base64
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from Core.decorator import Decorator as response_decorator
from Configuration.config import logger, config_ini_settings, expression_mapping, raise_exception
from Core.scraper import Scraper
# from mega import Mega  # Temporarily disabled due to version compatibility issues

@response_decorator
def no_preparation_download(self, url, json_entry=None, params=None, headers_only=False):
    resp = self.send_request(url)   
    return resp     

@response_decorator
def prepare_google(self, g_url, json_entry, params=None,headers_only=False):
    params.update(json_entry['Request Params'])
    resp = self.send_request(json_entry['URL'], params=params,headers_only=headers_only)
    for cookie, value in resp.cookies.items():
        if json_entry['Cookie'] in cookie:
            params['confirm'] = value
            break            
    resp = self.send_request(json_entry['URL'], params=params)
    return resp            

@response_decorator
def prepare_mediafire(self,mediafire_url, json_entry=None, params=None,headers_only=False):
    # Use simple BeautifulSoup parsing instead of Scraper class
    import requests
    from bs4 import BeautifulSoup
    
    response = self.send_request(mediafire_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for download button
    download_button = soup.find('a', id='downloadButton')
    if download_button and download_button.get('href'):
        download_link = download_button['href']
        resp = self.send_request(download_link, headers_only=headers_only)
        return resp
    
    # Fallback: try direct download
    resp = self.send_request(mediafire_url, headers_only=headers_only)
    return resp            

@response_decorator
def prepare_us_archive(self,us_archive_url, json_entry=None, params=None,headers_only=False):

    resp = self.send_request(us_archive_url,headers_only=headers_only)
    return resp            


@response_decorator
def prepare_datafilehost(self,dfh_url, json_entry, params=None,headers_only=False):
    cookies = {}
    resp = self.send_request(dfh_url,headers_only=headers_only)
    for cookie, value in resp.cookies.items():
        if 'PHPSESSID' in json_entry['Cookie']:
            cookies[cookie]=value
            break                
    resp = self.send_request(json_entry['URL'], params, cookies,headers_only=headers_only)
    return resp            

@response_decorator
def prepare_mega(self, mega_url, json_entry=None, params=None, headers_only=False):
    """Download files from Mega.nz using mega.py library with asyncio compatibility patch.
    
    mega.py uses deprecated asyncio.coroutine which was removed in Python 3.12.
    We patch asyncio before importing mega to maintain compatibility.
    """
    import requests
    import sys
    import os
    from pathlib import Path
    from io import BytesIO
    
    try:
        # Patch asyncio.coroutine for Python 3.12+ compatibility
        import asyncio
        import functools
        
        if sys.version_info >= (3, 12):
            # Python 3.12 removed asyncio.coroutine decorator
            # Create a minimal replacement
            if not hasattr(asyncio, 'coroutine'):
                def coroutine(func):
                    @functools.wraps(func)
                    def wrapped(*args, **kwargs):
                        return func(*args, **kwargs)
                    return wrapped
                asyncio.coroutine = coroutine
        
        # Now import mega.py
        from mega import Mega
        
        logger.info(f"Attempting Mega.nz download: {mega_url[:60]}...")
        
        # Initialize Mega client and download
        try:
            mega = Mega()
            timeout_seconds = getattr(self, 'mega_download_timeout_seconds', 900)
            
            # Create a temporary directory for download
            temp_dir = tempfile.mkdtemp()
            try:
                # mega.download_url can hang for a long time on some links.
                # Run it in a worker thread and enforce a hard timeout.
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(mega.download_url, mega_url, temp_dir)
                    try:
                        downloaded_path = future.result(timeout=timeout_seconds)
                    except FutureTimeoutError:
                        logger.error(
                            f"Mega.nz download timed out after {timeout_seconds}s: {mega_url}"
                        )
                        raise Exception(
                            f"Mega.nz download timed out after {timeout_seconds}s"
                        )
                
                if not downloaded_path:
                    raise Exception("Mega.nz returned None - file may not exist or server error")
                
                # Convert to string path if it's a Path object
                if isinstance(downloaded_path, Path):
                    downloaded_path = str(downloaded_path)
                
                # Read the file data
                if not os.path.exists(downloaded_path):
                    raise Exception(f"Downloaded file not found at {downloaded_path}")
                
                file_size = os.path.getsize(downloaded_path)
                if file_size == 0:
                    raise Exception("Downloaded file is empty")
                
                with open(downloaded_path, 'rb') as f:
                    file_data = f.read()
                
                # Create a custom response object that mimics requests.Response
                class MegaResponse:
                    def __init__(self, content, content_type='application/pdf', file_id='unknown'):
                        self._content = content
                        self.status_code = 200
                        self.headers = {
                            'Content-Type': content_type,
                            'Content-Length': str(len(content)),
                            'Content-Disposition': f'attachment; filename="mega_{file_id}.pdf"',
                            'content-disposition': f'attachment; filename="mega_{file_id}.pdf"',  # lowercase for compatibility
                            'content-length': str(len(content)),
                            'content-type': content_type
                        }
                        self._position = 0
                    
                    def read(self, amt=None):
                        if amt is None:
                            result = self._content[self._position:]
                            self._position = len(self._content)
                        else:
                            result = self._content[self._position:self._position + amt]
                            self._position += len(result)
                        return result
                    
                    def iter_content(self, chunk_size=1024):
                        """Iterate over response content in chunks."""
                        position = 0
                        while position < len(self._content):
                            chunk = self._content[position:position + chunk_size]
                            if chunk:
                                yield chunk
                            position += chunk_size
                    
                    def close(self):
                        """Close the response."""
                        pass
                
                # Extract file ID for naming
                if '/file/' in mega_url and '#' in mega_url:
                    file_id = mega_url.split('/file/')[-1].split('#')[0]
                elif '/#!' in mega_url:
                    file_id = mega_url.split('/#!')[-1].split('!')[0]
                else:
                    file_id = 'unknown'
                
                response = MegaResponse(file_data, 'application/pdf', file_id)
                
                logger.info(f"Successfully downloaded {len(file_data)} bytes from Mega.nz")
                return response
            
            finally:
                # Clean up temp directory
                import shutil
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Mega.nz download failed: {str(e)}")
            # Log for manual processing
            mega_manual_file = os.path.join(tempfile.gettempdir(), "mega_links_failed.txt")
            try:
                with open(mega_manual_file, 'a', encoding='utf-8') as f:
                    f.write(f"{mega_url} - Error: {str(e)}\n")
            except:
                pass
            raise Exception(f"Mega.nz download failed: {str(e)}")
    
    except ImportError as e:
        logger.error("mega.py not installed")
        raise Exception("mega.py library required. Install with: pip install mega.py")
    except Exception as e:
        raise
def prepare_eboi(self, eboi_url, json_entry=None, params=None, headers_only=False):
    """Handle eboi.org links - service appears to be down, so create error response."""
    import time
    
    try:
        # Try a very short timeout to detect if service is up
        response = self.send_request(eboi_url)
        # If we get here, the service responded
        return response
        
    except Exception as e:
        # Service is down or unreachable
        error_msg = f"eboi.org service unavailable: {str(e)}"
        logger.warning(error_msg)
        
        # Raise an exception that will be caught by the error handling
        raise_exception(error_msg)




