"""
PDF Book Crawler - Specialized web crawler for discovering and cataloging PDF books
"""

import re
import csv
import datetime
from typing import Set, List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import logging

from Core.config_manager import ConfigManager
from Core.http_client import HttpClient
from Core.scraper import Scraper
from Core.exceptions import ScrapingError


@dataclass
class BookMetadata:
    """Metadata for a discovered PDF book"""
    title: str
    author: str = "Unknown"
    website_name: str = ""
    source_url: str = ""
    file_size_mb: float = 0.0
    crawl_date: str = ""
    confidence_score: float = 0.0
    isbn: str = ""
    publication_year: str = ""
    
    def to_csv_row(self) -> List[str]:
        """Convert to CSV row format"""
        return [
            self.title,
            self.author,
            self.website_name,
            self.source_url,
            f"{self.file_size_mb:.2f}",
            self.crawl_date,
            f"{self.confidence_score:.2f}",
            self.isbn,
            self.publication_year
        ]


class PDFBookCrawler:
    """
    Specialized crawler for discovering PDF books with metadata extraction
    """
    
    def __init__(self, config_manager: ConfigManager, 
                 http_client: HttpClient, 
                 scraper: Scraper):
        
        self.config = config_manager
        self.http_client = http_client
        self.scraper = scraper
        self.logger = config_manager.get_logger()
        self.regex_manager = config_manager.get_regex_manager()
        
        # Book discovery settings
        self.min_book_size = config_manager.get_min_book_size_mb()
        self.csv_output_file = config_manager.get_book_csv_output_file()
        self.book_patterns = self.regex_manager.get_patterns_list('book_detection', 'book_keywords')
        self.extract_metadata = config_manager.get_extract_pdf_metadata()
        
        # Discovered books
        self.discovered_books: List[BookMetadata] = []
        
        # Get compiled patterns from regex manager
        self.author_patterns = self.regex_manager.get_patterns_list('book_detection', 'author_extraction')
        self.title_patterns = self.regex_manager.get_patterns_list('book_detection', 'title_extraction')
        self.isbn_pattern = self.regex_manager.get_pattern('book_detection', 'isbn_detection')
        self.year_pattern = self.regex_manager.get_pattern('book_detection', 'year_detection')
    
    def crawl_for_books(self, start_url: str, max_depth: int = 3, 
                       max_pages: int = 100) -> List[BookMetadata]:
        """
        Crawl a website specifically looking for PDF books
        
        Args:
            start_url: URL to start crawling from
            max_depth: Maximum depth to crawl
            max_pages: Maximum pages to visit
            
        Returns:
            List of discovered book metadata
        """
        
        self.logger.info(f"Starting PDF book discovery crawl from: {start_url}")
        start_time = datetime.datetime.now()
        
        # Reset discovered books
        self.discovered_books.clear()
        
        visited_pages = set()
        pages_to_visit = {start_url}
        website_name = self._extract_website_name(start_url)
        
        depth = 0
        
        try:
            while (pages_to_visit and 
                   depth < max_depth and 
                   len(visited_pages) < max_pages):
                
                self.logger.info(f"Crawling depth {depth + 1}/{max_depth}")
                
                # Process current level URLs
                current_level_urls = list(pages_to_visit)
                pages_to_visit.clear()
                
                for url in current_level_urls:
                    if len(visited_pages) >= max_pages:
                        break
                    
                    if url in visited_pages:
                        continue
                    
                    try:
                        # Discover books and new links on this page
                        page_books, new_links = self._crawl_page_for_books(
                            url, website_name, start_time.strftime('%Y-%m-%d %H:%M:%S')
                        )
                        
                        # Add discovered books
                        self.discovered_books.extend(page_books)
                        
                        # Add new links for next depth level
                        base_domain = self._get_domain(start_url)
                        for link in new_links:
                            if (link not in visited_pages and 
                                self._should_follow_link(link, base_domain)):
                                pages_to_visit.add(link)
                        
                        visited_pages.add(url)
                        
                        # Log progress
                        if page_books:
                            self.logger.info(f"Found {len(page_books)} books on {url}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to crawl {url}: {str(e)}")
                        continue
                
                depth += 1
            
            self.logger.info(f"Book discovery completed: {len(self.discovered_books)} books found, "
                           f"{len(visited_pages)} pages visited")
            
            return self.discovered_books.copy()
            
        except Exception as e:
            self.logger.error(f"Book crawl failed: {str(e)}")
            raise ScrapingError(start_url, f"PDF book crawl failed: {str(e)}")
    
    def _crawl_page_for_books(self, url: str, website_name: str, 
                            crawl_date: str) -> Tuple[List[BookMetadata], Set[str]]:
        """
        Crawl a single page for PDF books and extract metadata
        
        Returns:
            Tuple of (discovered_books, new_links_to_follow)
        """
        
        self.logger.debug(f"Scanning page for books: {url}")
        
        discovered_books = []
        new_links = set()
        
        try:
            # Get all links from the page
            all_links = self.scraper.get_links(url, element_type='a')
            
            if not all_links:
                return discovered_books, new_links
            
            for link_element in all_links:
                href = link_element.get('href')
                if not href:
                    continue
                
                # Convert to absolute URL
                absolute_url = urljoin(url, href)
                
                # Check if it's a PDF link
                if self._is_pdf_link(absolute_url):
                    # Classify if it's likely a book
                    book_metadata = self._classify_and_extract_book_metadata(
                        absolute_url, link_element, website_name, crawl_date
                    )
                    
                    if book_metadata and book_metadata.confidence_score > 0.3:
                        discovered_books.append(book_metadata)
                        self.logger.debug(f"Discovered book: {book_metadata.title}")
                
                # Add to links to follow if it's a page link
                elif self._is_followable_link(absolute_url):
                    new_links.add(absolute_url)
            
            return discovered_books, new_links
            
        except Exception as e:
            self.logger.error(f"Error crawling page {url} for books: {str(e)}")
            return discovered_books, new_links
    
    def _classify_and_extract_book_metadata(self, pdf_url: str, link_element, 
                                           website_name: str, crawl_date: str) -> Optional[BookMetadata]:
        """
        Classify PDF and extract book metadata
        """
        
        # Extract basic info from URL and link element
        filename = self._extract_filename_from_url(pdf_url)
        link_text = link_element.get_text(strip=True)
        
        # Initialize metadata
        metadata = BookMetadata(
            title=filename,
            website_name=website_name,
            source_url=pdf_url,
            crawl_date=crawl_date
        )
        
        # Calculate confidence score based on various factors
        confidence = 0.0
        
        # Check filename patterns for book indicators
        for pattern in self.book_patterns:
            if pattern.search(filename):
                confidence += 0.3
                break
        
        # Check link text for book indicators
        if any(keyword in link_text.lower() for keyword in 
               ['book', 'ebook', 'manual', 'guide', 'tutorial', 'textbook']):
            confidence += 0.2
        
        # Extract title from filename
        title = self._extract_title_from_filename(filename)
        if title and title != filename:
            metadata.title = title
            confidence += 0.1
        
        # Extract author from filename
        author = self._extract_author_from_filename(filename)
        if author:
            metadata.author = author
            confidence += 0.2
        
        # Look for ISBN in filename
        isbn_match = self.isbn_pattern.search(filename)
        if isbn_match:
            metadata.isbn = isbn_match.group(1)
            confidence += 0.3
        
        # Look for publication year
        year_match = self.year_pattern.search(filename)
        if year_match:
            metadata.publication_year = year_match.group(0)
            confidence += 0.1
        
        # Check file size if we can get it (HEAD request)
        try:
            file_size = self._estimate_file_size(pdf_url)
            if file_size:
                metadata.file_size_mb = file_size
                # Books are typically larger than 1MB
                if file_size >= self.min_book_size:
                    confidence += 0.2
                elif file_size < 0.5:
                    confidence -= 0.3  # Very small files unlikely to be books
        except:
            pass  # Size estimation failed, continue without it
        
        metadata.confidence_score = min(confidence, 1.0)
        
        return metadata if metadata.confidence_score > 0 else None
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """Extract book title from filename"""
        
        # Remove file extension
        name = filename.replace('.pdf', '').replace('.PDF', '')
        
        # Try various title extraction patterns
        for pattern in self.title_patterns:
            match = pattern.search(filename)
            if match:
                title = match.group(1)
                # Clean up title
                title = re.sub(r'[_-]', ' ', title)
                title = re.sub(r'\s+', ' ', title).strip()
                return title
        
        # Fallback: clean up the filename
        title = self.regex_manager.substitute('pdf_site_crawler.text_cleaning', 'underscores_hyphens', name, ' ')
        title = self.regex_manager.substitute('pdf_site_crawler.text_cleaning', 'multiple_spaces', title, ' ').strip()
        return title
    
    def _extract_author_from_filename(self, filename: str) -> str:
        """Extract author name from filename"""
        
        # Try various author extraction patterns
        for pattern in self.author_patterns:
            match = pattern.search(filename)
            if match:
                author = match.group(1)
                # Clean up author name
                author = self.regex_manager.substitute('pdf_site_crawler.text_cleaning', 'underscores_hyphens', author, ' ')
                author = self.regex_manager.substitute('pdf_site_crawler.text_cleaning', 'multiple_spaces', author, ' ').strip()
                # Check if it looks like a person's name
                if self._is_likely_person_name(author):
                    return author
        
        return ""
    
    def _is_likely_person_name(self, name: str) -> bool:
        """Check if a string looks like a person's name"""
        
        # Basic heuristics for person names
        words = name.split()
        
        # Should have 1-4 words
        if len(words) < 1 or len(words) > 4:
            return False
        
        # Each word should start with capital and be alphabetic
        for word in words:
            if not word or not word[0].isupper() or not word.isalpha():
                return False
        
        # Common name patterns
        if len(words) == 2:  # First Last
            return True
        elif len(words) == 3:  # First Middle Last or First M. Last
            return True
        elif len(words) == 1 and len(name) > 2:  # Single name
            return True
        
        return False
    
    def _estimate_file_size(self, url: str) -> Optional[float]:
        """Estimate file size in MB using HEAD request"""
        
        try:
            response = self.http_client.get(url, stream=True)
            content_length = response.headers.get('content-length')
            if content_length:
                size_bytes = int(content_length)
                return size_bytes / (1024 * 1024)  # Convert to MB
        except:
            pass  # Failed to get size
        
        return None
    
    def _is_pdf_link(self, url: str) -> bool:
        """Check if URL points to a PDF file"""
        return url.lower().endswith('.pdf')
    
    def _is_followable_link(self, url: str) -> bool:
        """Check if link should be followed for further crawling"""
        
        parsed = urlparse(url)
        
        # Must be HTTP/HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Skip common non-page files
        skip_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico', 
                          '.zip', '.rar', '.exe', '.pdf', '.doc', '.docx']
        
        for ext in skip_extensions:
            if url.lower().endswith(ext):
                return False
        
        return True
    
    def _should_follow_link(self, url: str, base_domain: str) -> bool:
        """Determine if a link should be followed"""
        
        # Stay within the same domain for focused crawling
        return self._get_domain(url) == base_domain
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _extract_website_name(self, url: str) -> str:
        """Extract website name from URL"""
        parsed = urlparse(url)
        return parsed.netloc
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL"""
        parsed = urlparse(url)
        filename = parsed.path.split('/')[-1] if parsed.path else ""
        return filename if filename else url
    
    def export_books_to_csv(self, output_file: Optional[str] = None) -> str:
        """
        Export discovered books to CSV file
        
        Args:
            output_file: Optional custom output file path
            
        Returns:
            Path to the created CSV file
        """
        
        csv_file = output_file or self.csv_output_file
        
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                # Write header
                writer.writerow([
                    'Title', 'Author', 'Website', 'Source URL', 'File Size (MB)',
                    'Crawl Date', 'Confidence Score', 'ISBN', 'Publication Year'
                ])
                
                # Write book data
                for book in self.discovered_books:
                    writer.writerow(book.to_csv_row())
            
            self.logger.info(f"Exported {len(self.discovered_books)} books to {csv_file}")
            return csv_file
            
        except Exception as e:
            self.logger.error(f"Failed to export books to CSV: {str(e)}")
            raise
    
    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get summary of book discovery results"""
        
        if not self.discovered_books:
            return {'total_books': 0}
        
        # Calculate statistics
        total_books = len(self.discovered_books)
        avg_confidence = sum(book.confidence_score for book in self.discovered_books) / total_books
        books_with_authors = sum(1 for book in self.discovered_books if book.author != "Unknown")
        books_with_isbn = sum(1 for book in self.discovered_books if book.isbn)
        total_size_mb = sum(book.file_size_mb for book in self.discovered_books)
        
        # Group by website
        websites = {}
        for book in self.discovered_books:
            if book.website_name not in websites:
                websites[book.website_name] = 0
            websites[book.website_name] += 1
        
        return {
            'total_books': total_books,
            'average_confidence': round(avg_confidence, 2),
            'books_with_authors': books_with_authors,
            'books_with_isbn': books_with_isbn,
            'total_size_mb': round(total_size_mb, 2),
            'books_per_website': websites,
            'highest_confidence_books': sorted(
                [(book.title, book.confidence_score) for book in self.discovered_books],
                key=lambda x: x[1], reverse=True
            )[:5]
        }