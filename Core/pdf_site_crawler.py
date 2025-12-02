"""
PDF Site Crawler - Comprehensive website crawler for PDF document discovery
Similar to GreenFlare DB functionality for crawling entire websites
"""

import re
import csv
import time
import datetime
import requests
from typing import Set, List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from dataclasses import dataclass, field
import logging
from collections import deque
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup

from Core.config_manager import ConfigManager
from Core.http_client import HttpClient
from Core.scraper import Scraper
from Core.exceptions import ScrapingError


@dataclass
class PDFDocument:
    """Represents a discovered PDF document with metadata"""
    url: str
    title: str = ""
    author: str = ""
    file_size_bytes: int = 0
    content_type: str = ""
    last_modified: str = ""
    discovered_on_page: str = ""
    discovery_date: str = ""
    response_code: int = 0
    depth: int = 0
    link_text: str = ""
    link_context: str = ""
    
    @property
    def file_size_mb(self) -> float:
        """File size in MB"""
        return self.file_size_bytes / (1024 * 1024) if self.file_size_bytes else 0.0
    
    @property
    def domain(self) -> str:
        """Extract domain from URL"""
        return urlparse(self.url).netloc
    
    def to_csv_row(self) -> List[str]:
        """Convert to CSV row format"""
        return [
            self.url,
            self.title,
            self.author,
            str(self.file_size_bytes),
            f"{self.file_size_mb:.2f}",
            self.content_type,
            self.last_modified,
            self.discovered_on_page,
            self.discovery_date,
            str(self.response_code),
            str(self.depth),
            self.link_text,
            self.link_context,
            self.domain
        ]


@dataclass
class CrawlStats:
    """Statistics for the crawl operation"""
    start_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    end_time: Optional[datetime.datetime] = None
    pages_crawled: int = 0
    pdfs_found: int = 0
    errors_encountered: int = 0
    duplicate_urls_skipped: int = 0
    external_urls_skipped: int = 0
    robots_blocked_urls: int = 0
    
    @property
    def duration_seconds(self) -> float:
        """Crawl duration in seconds"""
        end = self.end_time or datetime.datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def pages_per_second(self) -> float:
        """Pages crawled per second"""
        duration = self.duration_seconds
        return self.pages_crawled / duration if duration > 0 else 0


class PDFSiteCrawler:
    """
    Comprehensive website crawler for PDF document discovery
    Similar to GreenFlare DB functionality
    """
    
    def __init__(self, config_manager: ConfigManager, 
                 http_client: HttpClient, 
                 scraper: Scraper):
        
        self.config = config_manager
        self.http_client = http_client
        self.scraper = scraper
        self.logger = config_manager.get_logger()
        
        # Load crawler configuration
        self.max_pages = config_manager.get_max_pages_per_site()
        self.max_depth = config_manager.get_max_crawl_depth()
        self.request_delay = config_manager.get_request_delay()
        self.follow_external = config_manager.get_follow_external_links()
        self.extract_content = config_manager.get_extract_pdf_content()
        self.min_pdf_size = config_manager.get_min_pdf_size_kb() * 1024  # Convert to bytes
        self.max_pdf_size = config_manager.get_max_pdf_size_mb() * 1024 * 1024  # Convert to bytes
        
        # Output files
        self.csv_output = config_manager.get_pdf_documents_csv()
        self.sitemap_output = config_manager.get_sitemap_urls_file()
        
        # Crawler state
        self.discovered_pdfs: List[PDFDocument] = []
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.robots_parser: Optional[RobotFileParser] = None
        self.user_agent = "PDFSiteCrawler/1.0"
        
        # Statistics
        self.stats = CrawlStats()
        
        # PDF metadata extraction patterns
        self.title_patterns = [
            re.compile(r'([^/\\]+?)\.pdf$', re.IGNORECASE),
            re.compile(r'/([^/]+)\.pdf$', re.IGNORECASE),
        ]
        
        self.author_patterns = [
            re.compile(r'by[_\s-]+([A-Za-z\s\.]+)', re.IGNORECASE),
            re.compile(r'([A-Za-z\s\.]+)[_\s-]+-[_\s-]*[^/]*\.pdf', re.IGNORECASE),
            re.compile(r'/([A-Za-z]+[_\s]+[A-Za-z]+)[_\s-]*[^/]*\.pdf', re.IGNORECASE),
        ]
    
    def crawl_site(self, start_url: str, 
                   max_pages: Optional[int] = None,
                   max_depth: Optional[int] = None,
                   follow_external: Optional[bool] = None) -> List[PDFDocument]:
        """
        Crawl an entire website for PDF documents
        
        Args:
            start_url: URL to start crawling from
            max_pages: Maximum pages to crawl (overrides config)
            max_depth: Maximum depth to crawl (overrides config)
            follow_external: Whether to follow external links (overrides config)
            
        Returns:
            List of discovered PDF documents
        """
        
        # Override config if parameters provided
        if max_pages is not None:
            self.max_pages = max_pages
        if max_depth is not None:
            self.max_depth = max_depth
        if follow_external is not None:
            self.follow_external = follow_external
        
        self.logger.info(f"Starting comprehensive PDF site crawl of: {start_url}")
        self.logger.info(f"Config: max_pages={self.max_pages}, max_depth={self.max_depth}, "
                        f"follow_external={self.follow_external}")
        
        # Initialize crawler state
        self.stats = CrawlStats()
        self.discovered_pdfs.clear()
        self.crawled_urls.clear()
        self.failed_urls.clear()
        
        # Parse start URL
        parsed_start = urlparse(start_url)
        base_domain = f"{parsed_start.scheme}://{parsed_start.netloc}"
        
        # Load robots.txt
        self._load_robots_txt(base_domain)
        
        # Try to find and parse sitemap first
        sitemap_urls = self._discover_sitemap_urls(base_domain)
        if sitemap_urls:
            self.logger.info(f"Found sitemap with {len(sitemap_urls)} URLs")
            self._save_sitemap_urls(sitemap_urls)
        
        # Initialize crawl queue
        crawl_queue = deque([(start_url, 0)])  # (url, depth)
        
        try:
            while crawl_queue and len(self.crawled_urls) < self.max_pages:
                url, depth = crawl_queue.popleft()
                
                # Skip if already crawled or depth exceeded
                if url in self.crawled_urls or depth > self.max_depth:
                    continue
                
                # Check robots.txt
                if not self._can_crawl_url(url):
                    self.stats.robots_blocked_urls += 1
                    self.logger.debug(f"Blocked by robots.txt: {url}")
                    continue
                
                # Check domain restrictions
                if not self.follow_external and not self._is_same_domain(url, base_domain):
                    self.stats.external_urls_skipped += 1
                    continue
                
                try:
                    # Crawl the page
                    page_pdfs, new_urls = self._crawl_page_comprehensive(url, depth, base_domain)
                    
                    # Add discovered PDFs
                    self.discovered_pdfs.extend(page_pdfs)
                    self.stats.pdfs_found += len(page_pdfs)
                    
                    # Add new URLs to queue for next depth level
                    for new_url in new_urls:
                        if new_url not in self.crawled_urls:
                            crawl_queue.append((new_url, depth + 1))
                    
                    self.crawled_urls.add(url)
                    self.stats.pages_crawled += 1
                    
                    # Log progress
                    if self.stats.pages_crawled % 10 == 0:
                        self.logger.info(f"Progress: {self.stats.pages_crawled} pages crawled, "
                                       f"{self.stats.pdfs_found} PDFs found")
                    
                    # Rate limiting
                    if self.request_delay > 0:
                        time.sleep(self.request_delay)
                
                except Exception as e:
                    self.stats.errors_encountered += 1
                    self.failed_urls.add(url)
                    self.logger.error(f"Error crawling {url}: {str(e)}")
                    continue
            
            self.stats.end_time = datetime.datetime.now()
            
            self.logger.info(f"Site crawl completed! Found {len(self.discovered_pdfs)} PDFs "
                           f"across {self.stats.pages_crawled} pages in "
                           f"{self.stats.duration_seconds:.1f} seconds")
            
            return self.discovered_pdfs.copy()
            
        except KeyboardInterrupt:
            self.logger.info("Crawl interrupted by user")
            self.stats.end_time = datetime.datetime.now()
            return self.discovered_pdfs.copy()
        
        except Exception as e:
            self.logger.error(f"Site crawl failed: {str(e)}")
            self.stats.end_time = datetime.datetime.now()
            raise ScrapingError(start_url, f"Comprehensive site crawl failed: {str(e)}")
    
    def _crawl_page_comprehensive(self, url: str, depth: int, base_domain: str) -> Tuple[List[PDFDocument], Set[str]]:
        """
        Comprehensively crawl a single page for PDFs and links
        """
        
        self.logger.debug(f"Crawling page (depth {depth}): {url}")
        
        discovered_pdfs = []
        new_urls = set()
        
        try:
            # Get all links from the page
            all_links = self.scraper.get_links(url, element_type='a')
            
            if not all_links:
                return discovered_pdfs, new_urls
            
            for link_element in all_links:
                href = link_element.get('href')
                if not href:
                    continue
                
                # Convert to absolute URL
                absolute_url = urljoin(url, href)
                absolute_url = self._normalize_url(absolute_url)
                
                # Skip duplicates
                if absolute_url in self.crawled_urls:
                    self.stats.duplicate_urls_skipped += 1
                    continue
                
                # Check if it's a PDF link
                if self._is_pdf_url(absolute_url):
                    # Extract metadata and validate PDF
                    pdf_doc = self._process_pdf_link(absolute_url, link_element, url, depth)
                    
                    if pdf_doc:
                        discovered_pdfs.append(pdf_doc)
                        self.logger.debug(f"Discovered PDF: {pdf_doc.title}")
                
                # Add to links to follow if it's a page link
                elif self._should_crawl_url(absolute_url, base_domain):
                    new_urls.add(absolute_url)
            
            return discovered_pdfs, new_urls
            
        except Exception as e:
            self.logger.error(f"Error crawling page {url}: {str(e)}")
            return discovered_pdfs, new_urls
    
    def _process_pdf_link(self, pdf_url: str, link_element, source_page: str, depth: int) -> Optional[PDFDocument]:
        """
        Process a PDF link and extract metadata
        """
        
        try:
            # Create PDF document object first
            pdf_doc = PDFDocument(
                url=pdf_url,
                discovered_on_page=source_page,
                discovery_date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                response_code=0,  # Will be updated later
                depth=depth,
                link_text=link_element.get_text(strip=True)[:200],  # Limit length
                link_context=self._extract_link_context(link_element)
            )

            # Extract metadata from source page first (better for external services)
            page_metadata = self._extract_page_metadata(source_page)
            if page_metadata:
                pdf_doc.title = page_metadata.get('title', '')
                pdf_doc.author = page_metadata.get('author', '')
            
            # Try to get file info from external service
            parsed_url = urlparse(pdf_url)
            if parsed_url.netloc.lower() in ['mega.nz', 'drive.google.com', 'mediafire.com', 'dropbox.com']:
                # For external services, we'll record them as found PDFs but may not get full metadata
                pdf_doc.content_type = 'application/pdf (external service)'
                pdf_doc.response_code = 200  # Assume available if link exists
                
                # Try to get better title from link text or page context
                if not pdf_doc.title:
                    pdf_doc.title = self._extract_title_from_context(link_element, source_page)
                
                return pdf_doc
            
            else:
                # For direct PDF links, try to get actual file info
                response = self.http_client.head(pdf_url)
                pdf_doc.response_code = response.status_code
                
                if response.status_code != 200:
                    self.logger.warning(f"PDF returned {response.status_code}: {pdf_url}")
                    return pdf_doc  # Return with error info
                
                # Extract metadata from headers
                headers = response.headers
                pdf_doc.content_type = headers.get('content-type', '')
                pdf_doc.last_modified = headers.get('last-modified', '')
                
                # Get file size
                content_length = headers.get('content-length')
                if content_length:
                    pdf_doc.file_size_bytes = int(content_length)
                    
                    # Check size limits
                    if pdf_doc.file_size_bytes < self.min_pdf_size:
                        self.logger.debug(f"PDF too small ({pdf_doc.file_size_mb:.2f} MB): {pdf_url}")
                        return None
                    
                    if pdf_doc.file_size_bytes > self.max_pdf_size:
                        self.logger.debug(f"PDF too large ({pdf_doc.file_size_mb:.2f} MB): {pdf_url}")
                        return None
                
                # Fallback title extraction if not found on page
                if not pdf_doc.title:
                    pdf_doc.title = self._extract_title_from_url(pdf_url)
            
            return pdf_doc
            
        except Exception as e:
            self.logger.error(f"Error processing PDF link {pdf_url}: {str(e)}")
            return None
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract title from PDF URL"""
        
        # Get filename
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        
        # Remove extension
        title = filename.replace('.pdf', '').replace('.PDF', '')
        
        # Clean up title
        title = re.sub(r'[_-]', ' ', title)
        title = re.sub(r'%20', ' ', title)  # URL decode spaces
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _extract_author_from_url(self, url: str) -> str:
        """Extract author from PDF URL using patterns"""
        
        for pattern in self.author_patterns:
            match = pattern.search(url)
            if match:
                author = match.group(1)
                author = re.sub(r'[_-]', ' ', author)
                author = re.sub(r'\s+', ' ', author).strip()
                
                # Basic validation - should look like a person's name
                if self._is_likely_author_name(author):
                    return author
        
        return ""
    
    def _is_likely_author_name(self, name: str) -> bool:
        """Check if a string looks like an author name"""
        
        words = name.split()
        
        # Should have 1-4 words
        if len(words) < 1 or len(words) > 4:
            return False
        
        # Single character names are unlikely to be real authors
        if len(name.strip()) < 2:
            return False
        
        # Each word should be mostly alphabetic
        for word in words:
            if not word or len([c for c in word if c.isalpha()]) / len(word) < 0.7:
                return False
            # Single character words are suspicious unless they're initials
            if len(word) == 1 and len(words) == 1:
                return False
        
        return True
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize title text"""
        
        # Remove common unwanted phrases
        unwanted_phrases = [
            'download', 'pdf', 'click here', 'read more', 'full text',
            'view', 'open', 'file', 'document', '[pdf]', '(pdf)'
        ]
        
        cleaned = title.lower()
        for phrase in unwanted_phrases:
            cleaned = cleaned.replace(phrase, ' ')
        
        # Clean up whitespace and restore case
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # If too short after cleaning, return original
        if len(cleaned) < 3:
            return title.strip()
        
        # Title case the result
        return cleaned.title()
    
    def _extract_link_context(self, link_element) -> str:
        """Extract context around the link for better understanding"""
        
        try:
            # Get parent element text for context
            parent = link_element.parent
            if parent:
                context = parent.get_text(strip=True)
                return context[:500]  # Limit length
        except:
            pass
        
        return ""
    
    def _extract_page_metadata(self, source_page_url: str) -> Optional[dict]:
        """Extract metadata from the source page for better book information"""
        
        try:
            # Cache the page content if we already have it
            if hasattr(self, '_page_cache') and source_page_url in self._page_cache:
                soup = self._page_cache[source_page_url]
            else:
                response = self.http_client.get(source_page_url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Simple caching
                if not hasattr(self, '_page_cache'):
                    self._page_cache = {}
                self._page_cache[source_page_url] = soup
            
            metadata = {}
            
            # Get page title and h1 for analysis
            title_element = soup.find('title')
            h1_element = soup.find('h1')
            
            page_title = title_element.get_text(strip=True) if title_element else ''
            h1_title = h1_element.get_text(strip=True) if h1_element else ''
            
            # Extract title and author from page title pattern: "Bengali Title - Author | English Title - Author"
            if page_title:
                # Split by pipe to get the main part
                main_part = page_title.split(' | ')[0] if ' | ' in page_title else page_title
                
                # Look for pattern "Title - Author"
                title_author_match = re.search(r'^(.+?)\s*[-–]\s*([^|]+?)(?:\s+pdf)?$', main_part)
                if title_author_match:
                    title_part = title_author_match.group(1).strip()
                    author_part = title_author_match.group(2).strip()
                    
                    # Clean up title and author
                    if len(author_part) < 50 and 'bangla' not in author_part.lower():
                        metadata['title'] = title_part
                        metadata['author'] = author_part
                    
            # Fallback: use h1 for title if not found
            if 'title' not in metadata and h1_title:
                # Clean h1 title
                clean_title = re.sub(r'\s*pdf\s*', ' ', h1_title, flags=re.IGNORECASE)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                metadata['title'] = clean_title
            
            # Try alternative author extraction if not found
            if 'author' not in metadata:
                # Look for author in visible text
                for elem in soup.find_all(['span', 'div', 'p', 'a']):
                    text = elem.get_text(strip=True)
                    # Look for Bengali names (reasonable length with Bengali characters)
                    if (5 <= len(text) <= 30 and 
                        any(char in text for char in 'অআইঈউঊএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়') and
                        not any(word in text.lower() for word in ['home', 'menu', 'blog', 'contact', 'download', 'link', 'share'])):
                        
                        # Check if this might be an author name
                        parent_text = elem.parent.get_text(strip=True) if elem.parent else ''
                        if 'লেখক' in parent_text or len(text.split()) <= 3:  # Author indicator or short name
                            metadata['author'] = text
                            break
            
            return metadata if metadata else None
            
        except Exception as e:
            self.logger.debug(f"Could not extract page metadata from {source_page_url}: {str(e)}")
            return None
    
    def _extract_title_from_context(self, link_element, source_page_url: str) -> str:
        """Extract title from link context and surrounding elements"""
        
        try:
            # Try link text first
            link_text = link_element.get_text(strip=True)
            if link_text and len(link_text) > 3 and not link_text.lower().startswith('link'):
                return self._clean_title(link_text)
            
            # Look at parent elements for context
            current = link_element.parent
            for _ in range(3):  # Check up to 3 parent levels
                if current:
                    heading = current.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading:
                        title = heading.get_text(strip=True)
                        if title and len(title) > 3:
                            return self._clean_title(title)
                    current = current.parent
                else:
                    break
            
            # Look for title in page metadata
            page_metadata = self._extract_page_metadata(source_page_url)
            if page_metadata and 'title' in page_metadata:
                return page_metadata['title']
            
            # Fallback to URL-based title
            return self._extract_title_from_url(source_page_url)
            
        except Exception as e:
            self.logger.debug(f"Could not extract title from context: {str(e)}")
            return "Unknown Title"

    def _discover_sitemap_urls(self, base_domain: str) -> List[str]:
        """Discover and parse sitemap URLs"""
        
        sitemap_urls = []
        
        # Common sitemap locations
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemaps.xml',
            '/sitemap.txt'
        ]
        
        for path in sitemap_paths:
            try:
                sitemap_url = base_domain + path
                response = self.http_client.get(sitemap_url)
                
                if response.status_code == 200:
                    self.logger.info(f"Found sitemap: {sitemap_url}")
                    
                    if path.endswith('.xml'):
                        urls = self._parse_xml_sitemap(response.text)
                    else:
                        urls = self._parse_text_sitemap(response.text)
                    
                    sitemap_urls.extend(urls)
                    break  # Use first found sitemap
                    
            except Exception as e:
                self.logger.debug(f"Could not access sitemap {sitemap_url}: {str(e)}")
                continue
        
        return sitemap_urls
    
    def _parse_xml_sitemap(self, xml_content: str) -> List[str]:
        """Parse XML sitemap and extract URLs"""
        
        urls = []
        try:
            root = ET.fromstring(xml_content)
            
            # Handle different namespace possibilities
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            for url_elem in root.findall('.//sitemap:url', namespaces):
                loc_elem = url_elem.find('sitemap:loc', namespaces)
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text.strip())
            
            # Fallback for sitemaps without namespace
            if not urls:
                for url_elem in root.findall('.//url'):
                    loc_elem = url_elem.find('loc')
                    if loc_elem is not None and loc_elem.text:
                        urls.append(loc_elem.text.strip())
                        
        except ET.ParseError as e:
            self.logger.warning(f"Could not parse XML sitemap: {str(e)}")
        
        return urls
    
    def _parse_text_sitemap(self, text_content: str) -> List[str]:
        """Parse text sitemap (one URL per line)"""
        
        urls = []
        for line in text_content.splitlines():
            line = line.strip()
            if line and line.startswith('http'):
                urls.append(line)
        
        return urls
    
    def _save_sitemap_urls(self, urls: List[str]):
        """Save discovered sitemap URLs to file"""
        
        try:
            with open(self.sitemap_output, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(url + '\n')
            
            self.logger.info(f"Saved {len(urls)} sitemap URLs to {self.sitemap_output}")
            
        except Exception as e:
            self.logger.error(f"Failed to save sitemap URLs: {str(e)}")
    
    def _load_robots_txt(self, base_domain: str):
        """Load and parse robots.txt"""
        
        try:
            robots_url = base_domain + '/robots.txt'
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            
            self.logger.info(f"Loaded robots.txt from {robots_url}")
            
        except Exception as e:
            self.logger.debug(f"Could not load robots.txt: {str(e)}")
            self.robots_parser = None
    
    def _can_crawl_url(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        
        if not self.robots_parser:
            return True
        
        try:
            return self.robots_parser.can_fetch(self.user_agent, url)
        except:
            return True  # Allow if check fails
    
    def _is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF file or external download service"""
        
        parsed = urlparse(url)
        path = parsed.path.lower()
        domain = parsed.netloc.lower()
        
        # Exclude social media sharing URLs
        excluded_domains = {
            'pinterest.com', 'tumblr.com', 'reddit.com', 'facebook.com', 
            'twitter.com', 'linkedin.com', 'share.flipboard.com'
        }
        
        if any(excluded_domain in domain for excluded_domain in excluded_domains):
            return False
        
        # Direct PDF files
        if path.endswith('.pdf') or path.endswith('.pdf/') or 'application/pdf' in url.lower():
            return True
        
        # External download services that host PDFs
        external_pdf_services = {
            'mega.nz': True,
            'mediafire.com': 'pdf' in url.lower(),  # Only if PDF in URL
            'drive.google.com': True,
            'dropbox.com': True,
            'docdro.id': True,
            'userscloud.com': True,
            'app.box.com': True,
            'scribd.com': True,
            'academia.edu': True,
            'researchgate.net': True
        }
        
        for service_domain, condition in external_pdf_services.items():
            if service_domain in domain:
                return condition if isinstance(condition, bool) else condition
        
        return False
    
    def _should_crawl_url(self, url: str, base_domain: str) -> bool:
        """Determine if URL should be crawled"""
        
        parsed = urlparse(url)
        
        # Must be HTTP/HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check domain restrictions
        if not self.follow_external and not self._is_same_domain(url, base_domain):
            return False
        
        # Skip common non-page files
        skip_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
            '.css', '.js', '.woff', '.woff2', '.ttf',
            '.zip', '.rar', '.gz', '.tar', '.exe', '.msi',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        ]
        
        path = parsed.path.lower()
        for ext in skip_extensions:
            if path.endswith(ext):
                return False
        
        # Skip common non-content paths
        skip_paths = [
            '/admin/', '/wp-admin/', '/api/', '/ajax/',
            '/login/', '/register/', '/logout/', '/search/',
            '/feed/', '/rss/', '/atom/', '/sitemap'
        ]
        
        for skip_path in skip_paths:
            if skip_path in path:
                return False
        
        return True
    
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain"""
        
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        
        # Remove www prefix for comparison
        domain1 = domain1.replace('www.', '')
        domain2 = domain2.replace('www.', '')
        
        return domain1 == domain2
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and unnecessary query params"""
        
        parsed = urlparse(url)
        
        # Remove fragment
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # No fragment
        ))
        
        return normalized
    
    def export_to_csv(self, output_file: Optional[str] = None) -> str:
        """Export discovered PDFs to CSV file"""
        
        csv_file = output_file or self.csv_output
        
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                # Write header
                writer.writerow([
                    'URL', 'Title', 'Author', 'File Size (Bytes)', 'File Size (MB)',
                    'Content Type', 'Last Modified', 'Discovered On Page',
                    'Discovery Date', 'Response Code', 'Depth', 'Link Text',
                    'Link Context', 'Domain'
                ])
                
                # Write PDF data
                for pdf in self.discovered_pdfs:
                    writer.writerow(pdf.to_csv_row())
            
            self.logger.info(f"Exported {len(self.discovered_pdfs)} PDFs to {csv_file}")
            return csv_file
            
        except Exception as e:
            self.logger.error(f"Failed to export PDFs to CSV: {str(e)}")
            raise
    
    def get_crawl_summary(self) -> Dict[str, Any]:
        """Get comprehensive crawl statistics"""
        
        total_pdfs = len(self.discovered_pdfs)
        
        if total_pdfs == 0:
            return {
                'total_pdfs': 0,
                'crawl_stats': self.stats.__dict__,
                'domains': {},
                'file_sizes': {},
                'largest_pdfs': [],
                'most_recent_pdfs': []
            }
        
        # Group PDFs by domain
        domains = {}
        file_sizes = {'small': 0, 'medium': 0, 'large': 0}
        total_size_bytes = 0
        
        for pdf in self.discovered_pdfs:
            # Count by domain
            domain = pdf.domain
            domains[domain] = domains.get(domain, 0) + 1
            
            # Categorize by file size
            size_mb = pdf.file_size_mb
            if size_mb < 1:
                file_sizes['small'] += 1
            elif size_mb < 10:
                file_sizes['medium'] += 1
            else:
                file_sizes['large'] += 1
            
            total_size_bytes += pdf.file_size_bytes
        
        # Get largest PDFs
        largest_pdfs = sorted(
            [(pdf.title or pdf.url, pdf.file_size_mb, pdf.url) 
             for pdf in self.discovered_pdfs],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        # Get most recent PDFs (by discovery date)
        most_recent = sorted(
            [(pdf.title or pdf.url, pdf.discovery_date, pdf.url)
             for pdf in self.discovered_pdfs],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        return {
            'total_pdfs': total_pdfs,
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'average_size_mb': (total_size_bytes / (1024 * 1024)) / total_pdfs,
            'crawl_stats': {
                'duration_seconds': self.stats.duration_seconds,
                'pages_crawled': self.stats.pages_crawled,
                'pages_per_second': self.stats.pages_per_second,
                'pdfs_found': self.stats.pdfs_found,
                'errors_encountered': self.stats.errors_encountered,
                'duplicate_urls_skipped': self.stats.duplicate_urls_skipped,
                'external_urls_skipped': self.stats.external_urls_skipped,
                'robots_blocked_urls': self.stats.robots_blocked_urls
            },
            'domains': domains,
            'file_sizes': file_sizes,
            'largest_pdfs': largest_pdfs,
            'most_recent_pdfs': most_recent,
            'pdfs_with_authors': len([p for p in self.discovered_pdfs if p.author]),
            'unique_domains': len(domains),
            'failed_urls': len(self.failed_urls)
        }