import itertools
import functools
from typing import Optional, Dict, Tuple, Any
import requests
import re, traceback, logging, configparser, json, os, sys, warnings, datetime, time
from Core.decorator import Decorator as response_decorator
from Configuration.config import logger, config_ini_settings, expression_mapping, raise_exception
from clint.textui import progress
import  Core.download_strategies as strategies
from tqdm import tqdm

#https://mega.nz/file/rstD0S4a#mcGTRB3h7Q_I1k5LA5YPoo2lYGftStktGenNWersE5o

class Downloader():

    def __init__(self, custom_download_folder: Optional[str] = None) -> None:
        try:
            logger.info('Starting Logger')
            self.scraped_links: str = config_ini_settings['Filenames']['scraped-links']
            self.download_folder: str = custom_download_folder or config_ini_settings['Filenames']['download-folder']
            # Ensure download folder ends with path separator
            if not self.download_folder.endswith('/') and not self.download_folder.endswith('\\'):
                self.download_folder += '/' 
            self.download_errors: str = config_ini_settings['Filenames']['download-errors']
            self.request_header: Dict[str, str] = {'user-agent': config_ini_settings['Values']['user-agent']}
            self.session: requests.Session = requests.session()
            self.request_timeout: Tuple[int, int] = (10, 60)
            self.max_retries: int = 3
            self.retry_backoff_seconds: int = 5
            self.mega_download_timeout_seconds: int = 900
            # Track filenames for duplicate detection
            self.filename_counts: Dict[str, int] = {}
            self.prepare_function: Dict[str, Any] = {
                'mega.nz': strategies.prepare_mega,
                'drive.google.com': strategies.prepare_google, 
                'www.datafilehost.com': strategies.prepare_datafilehost, 
                'mediafire.com': strategies.no_preparation_download, 
                'www.mediafire.com': strategies.prepare_mediafire,
                'box.com': strategies.no_preparation_download,
                'www.box.com': strategies.no_preparation_download,
                'app.box.com': strategies.no_preparation_download,
                'dropbox.com': strategies.no_preparation_download,
                'www.dropbox.com': strategies.no_preparation_download,
                'substack.com': strategies.no_preparation_download,
                'eboi.org': strategies.prepare_eboi
            }
        except Exception as e:
            logger.exception(e)
            print(e)

    def __enter__(self) -> 'Downloader':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close the session if needed
        if hasattr(self, 'session'):
            self.session.close()
        return False


    def send_request(self, url: str, params: Optional[Dict[str, Any]] = None,
                     cookies: Optional[Dict[str, str]] = None,
                     headers_only: bool = False) -> requests.Response:

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(
                    url,
                    headers=self.request_header,
                    params=params,
                    cookies=cookies,
                    stream=True,
                    timeout=self.request_timeout,
                )

                if resp.status_code == 200:
                    return resp

                if resp.status_code in {429, 500, 502, 503, 504}:
                    logger.warning(
                        f"Request returned status code {resp.status_code} for {url} (attempt {attempt}/{self.max_retries})"
                    )
                    time.sleep(self.retry_backoff_seconds)
                    continue

                raise_exception(self, f"Request returned status code {resp.status_code} for {url}")

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                logger.warning(
                    f"Request failed for {url} (attempt {attempt}/{self.max_retries}): {e}"
                )
                time.sleep(self.retry_backoff_seconds)
            except Exception as e:
                last_error = e
                logger.error(f"Request failed for {url}: {e}")
                break

        if last_error:
            raise_exception(self, f"Request failed after {self.max_retries} attempts for {url}: {last_error}")

        raise_exception(self, f"Request failed after {self.max_retries} attempts for {url}")

    def download_file(self, file_url: str, book_title: Optional[str] = None) -> Optional[Tuple[str, int]]:
        """Download a file from the given URL with error page detection"""
        book_info = None
        download_host_regex_match = re.search(expression_mapping['Download Link RegEx'], file_url)
        
        try:            
            if not download_host_regex_match:
                error_msg = f"Invalid URL format: {file_url}"
                print(error_msg)
                logger.error(error_msg)
                return None
            
            download_host = download_host_regex_match.group(1)
            if download_host not in expression_mapping["Download URL"]:
                print(f"{download_host} is not a known URL")
                logger.error(f"{download_host} is not a known URL")
                return None
            
            with self.prepare_function[download_host](self, file_url) as resp:
                # Get actual filename from PDF's Content-Disposition header
                actual_pdf_filename = None
                if 'content-disposition' in resp.headers:
                    try:
                        actual_pdf_filename = re.findall("filename=\"(.+)\";*", resp.headers["Content-Disposition"])[0]
                    except:
                        pass
                
                # Check if the CSV/JSON filename is a duplicate
                if book_title:
                    if book_title not in self.filename_counts:
                        self.filename_counts[book_title] = 0
                    self.filename_counts[book_title] += 1
                    
                    # If this is a duplicate (count > 1), prefer the PDF's actual filename
                    if self.filename_counts[book_title] > 1 and actual_pdf_filename:
                        logger.info(f"Duplicate filename detected: '{book_title}' - using PDF's actual filename: '{actual_pdf_filename}'")
                        book_title = actual_pdf_filename
                
                # Fallback: no provided title, use PDF filename or generate one
                if not book_title:
                    if actual_pdf_filename:
                        book_title = actual_pdf_filename
                        logger.debug(f"Using PDF filename: {book_title}")
                    else:
                        book_title = f"download_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        logger.warning(f"No title provided and no Content-Disposition header - using: {book_title}")
                
                # Check if file already exists
                file_exists = False
                for e in expression_mapping['File Extensions']:
                    file_path_check = os.path.join(os.getcwd(), self.download_folder, book_title + '.' + e)
                    if os.path.isfile(file_path_check):
                        file_exists = True
                        break
                
                if file_exists:
                    logger.info(f"{book_title} already exists")
                    print(f"{book_title} already exists")
                    return None
                
                # Ensure download directory exists
                download_dir = os.path.join(os.getcwd(), self.download_folder)
                os.makedirs(download_dir, exist_ok=True)
                
                file_path = os.path.join(download_dir, book_title)
                
                # Collect the response content to check for errors
                content = b''
                total_length = resp.headers.get('content-length')
                total_length = int(total_length) if total_length else 0
                
                if total_length > 0:
                    for chunk in progress.bar(resp.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
                        if chunk:
                            content += chunk
                else:
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            content += chunk
                
                # Check if we got an error page instead of the actual file
                content_lower = content.lower()
                error_indicators = [
                    b'<!doctype html',
                    b'<html',
                    b'<head',
                    b'accounts.google.com',
                    b'login',
                    b'authenticate',
                    b'unauthorized',
                    b'access denied',
                    b'404 not found',
                    b'500 internal server error',
                    b'cloudflare',
                    b'recaptcha',
                ]
                
                is_error_page = False
                for indicator in error_indicators:
                    if indicator in content_lower:
                        is_error_page = True
                        break
                
                if is_error_page:
                    logger.error(f"Downloaded an error/login page instead of PDF: {book_title}")
                    logger.error(f"Content preview: {content[:200]}")
                    # Don't save this file
                    return None
                
                # Determine file extension from content-type header
                content_type = resp.headers.get('content-type', 'application/pdf').lower()
                if 'pdf' in content_type:
                    extension = '.pdf'
                elif 'plain' in content_type or 'text' in content_type:
                    extension = '.txt'
                elif 'html' in content_type:
                    extension = '.html'
                else:
                    extension = '.pdf'  # Default to PDF for unknown types
                
                # Append extension if not already in filename
                if not book_title.endswith(extension):
                    file_path = file_path + extension
                
                # Write the collected content to file
                with open(file_path, 'wb') as pdf_file, open(self.scraped_links, 'a+', encoding='utf-8') as scraped_links:
                    pdf_file.write(content)
                    size = len(content)
                    book_info = (os.path.basename(file_path), size)
                    scraped_links.writelines("\n" + os.path.basename(file_path) + ": " + str(size/(1024**2)) + " Megabytes\n")
                
        except Exception as e:
            error_msg = f"Download error for {file_url}: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            with open(self.download_errors, 'a', encoding='utf-8') as d:
                d.write(f"\nError downloading: {file_url} - {str(e)}\n")
        
        return book_info

