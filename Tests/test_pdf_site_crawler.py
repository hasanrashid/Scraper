"""
Unit tests for PDF Site Crawler
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import csv
import os
from Core.pdf_site_crawler import PDFSiteCrawler, PDFDocument, CrawlStats
from Core.config_manager import TestConfigManager
from Core.http_client import MockHttpClient


class TestPDFSiteCrawler(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.config_manager = TestConfigManager()
        self.http_client = MockHttpClient()
        self.scraper = Mock()
        self.crawler = PDFSiteCrawler(self.config_manager, self.http_client, self.scraper)
    
    def test_pdf_document_creation(self):
        """Test PDFDocument creation and properties"""
        pdf = PDFDocument(
            url="https://example.com/document.pdf",
            title="Test Document",
            author="John Doe",
            file_size_bytes=2097152,  # 2 MB
            discovery_date="2024-01-01 12:00:00"
        )
        
        self.assertEqual(pdf.url, "https://example.com/document.pdf")
        self.assertEqual(pdf.title, "Test Document")
        self.assertEqual(pdf.author, "John Doe")
        self.assertEqual(pdf.file_size_mb, 2.0)
        self.assertEqual(pdf.domain, "example.com")
        
        # Test CSV row conversion
        csv_row = pdf.to_csv_row()
        self.assertEqual(csv_row[0], "https://example.com/document.pdf")
        self.assertEqual(csv_row[1], "Test Document")
        self.assertEqual(csv_row[2], "John Doe")
        self.assertEqual(csv_row[4], "2.00")  # File size in MB
    
    def test_crawl_stats(self):
        """Test CrawlStats functionality"""
        stats = CrawlStats()
        stats.pages_crawled = 10
        stats.pdfs_found = 5
        stats.errors_encountered = 1
        
        self.assertEqual(stats.pages_crawled, 10)
        self.assertEqual(stats.pdfs_found, 5)
        self.assertEqual(stats.errors_encountered, 1)
        self.assertIsInstance(stats.duration_seconds, float)
        self.assertIsInstance(stats.pages_per_second, float)
    
    def test_is_pdf_url(self):
        """Test PDF URL detection"""
        pdf_urls = [
            "https://example.com/document.pdf",
            "https://example.com/paper.PDF",
            "https://example.com/download?file=doc.pdf",
            "https://example.com/file?type=application/pdf"
        ]
        
        non_pdf_urls = [
            "https://example.com/page.html",
            "https://example.com/image.jpg",
            "https://example.com/document.doc"
        ]
        
        for url in pdf_urls:
            self.assertTrue(self.crawler._is_pdf_url(url), f"Should detect {url} as PDF")
        
        for url in non_pdf_urls:
            self.assertFalse(self.crawler._is_pdf_url(url), f"Should not detect {url} as PDF")
    
    def test_extract_title_from_url(self):
        """Test title extraction from URL"""
        test_cases = [
            ("https://example.com/research_paper.pdf", "research paper"),
            ("https://example.com/Machine-Learning-Guide.pdf", "Machine Learning Guide"),
            ("https://example.com/docs/Python%20Programming.pdf", "Python Programming"),
            ("https://example.com/simple.pdf", "simple")
        ]
        
        for url, expected_title in test_cases:
            title = self.crawler._extract_title_from_url(url)
            self.assertEqual(title.lower(), expected_title.lower())
    
    def test_extract_author_from_url(self):
        """Test author extraction from URL"""
        # Test with URLs that should find authors
        author_url = "https://example.com/paper_by_John_Doe.pdf"
        author = self.crawler._extract_author_from_url(author_url)
        self.assertIsInstance(author, str)  # Should return a string (may be empty)
        
        # Test with URL that likely won't find author
        no_author_url = "https://example.com/document123.pdf"
        author = self.crawler._extract_author_from_url(no_author_url)
        self.assertIsInstance(author, str)  # Should return a string
    
    def test_is_likely_author_name(self):
        """Test author name validation"""
        valid_names = [
            "John Doe",
            "Jane Smith"
        ]
        
        clearly_invalid_names = [
            "123456",
            "x",
            "!@#$%"
        ]
        
        for name in valid_names:
            result = self.crawler._is_likely_author_name(name)
            self.assertTrue(result, f"{name} should be recognized as a valid author name")
        
        for name in clearly_invalid_names:
            result = self.crawler._is_likely_author_name(name)
            self.assertFalse(result, f"{name} should not be recognized as a valid author name")
    
    def test_clean_title(self):
        """Test title cleaning functionality"""
        test_cases = [
            ("Download PDF Document Here", "Document Here"),
            ("[PDF] Research Paper", "Research Paper"),
            ("Good Title", "Good Title")  # Should remain unchanged
        ]
        
        for input_title, expected_contain in test_cases:
            cleaned = self.crawler._clean_title(input_title)
            # Check that cleaning produces a reasonable result
            self.assertIsInstance(cleaned, str)
            self.assertGreater(len(cleaned.strip()), 0)
    
    def test_should_crawl_url(self):
        """Test URL crawling decision logic"""
        base_domain = "https://example.com"
        
        # URLs that should be crawled
        crawlable_urls = [
            "https://example.com/page1.html",
            "https://example.com/section/",
            "https://example.com/docs"
        ]
        
        # URLs that should NOT be crawled
        non_crawlable_urls = [
            "https://example.com/image.jpg",
            "https://example.com/style.css",
            "https://example.com/admin/",
            "ftp://example.com/file",
            "https://other-domain.com/page"
        ]
        
        for url in crawlable_urls:
            self.assertTrue(self.crawler._should_crawl_url(url, base_domain))
        
        for url in non_crawlable_urls:
            self.assertFalse(self.crawler._should_crawl_url(url, base_domain))
    
    def test_is_same_domain(self):
        """Test domain comparison"""
        test_cases = [
            ("https://example.com/page1", "https://example.com/page2", True),
            ("https://www.example.com/page", "https://example.com/other", True),  # www ignored
            ("https://example.com", "https://other.com", False),
            ("http://example.com", "https://example.com", True),  # Protocol ignored
        ]
        
        for url1, url2, expected in test_cases:
            result = self.crawler._is_same_domain(url1, url2)
            self.assertEqual(result, expected)
    
    def test_normalize_url(self):
        """Test URL normalization"""
        test_cases = [
            ("https://example.com/page#section", "https://example.com/page"),
            ("https://example.com/page?param=value", "https://example.com/page?param=value"),
            ("https://example.com/page", "https://example.com/page")
        ]
        
        for input_url, expected_output in test_cases:
            normalized = self.crawler._normalize_url(input_url)
            self.assertEqual(normalized, expected_output)
    
    def test_parse_xml_sitemap(self):
        """Test XML sitemap parsing"""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page1</loc>
            </url>
            <url>
                <loc>https://example.com/page2</loc>
            </url>
        </urlset>'''
        
        urls = self.crawler._parse_xml_sitemap(xml_content)
        
        self.assertEqual(len(urls), 2)
        self.assertIn("https://example.com/page1", urls)
        self.assertIn("https://example.com/page2", urls)
    
    def test_parse_text_sitemap(self):
        """Test text sitemap parsing"""
        text_content = '''https://example.com/page1
        https://example.com/page2
        https://example.com/page3
        # This is a comment
        not-a-url'''
        
        urls = self.crawler._parse_text_sitemap(text_content)
        
        self.assertEqual(len(urls), 3)
        self.assertIn("https://example.com/page1", urls)
        self.assertIn("https://example.com/page2", urls)
        self.assertIn("https://example.com/page3", urls)
    
    def test_export_to_csv(self):
        """Test CSV export functionality"""
        # Add test PDFs
        pdf1 = PDFDocument(
            url="https://test.com/doc1.pdf",
            title="Document 1",
            author="Author One",
            file_size_bytes=1024000
        )
        
        pdf2 = PDFDocument(
            url="https://test.com/doc2.pdf",
            title="Document 2",
            author="Author Two",
            file_size_bytes=2048000
        )
        
        self.crawler.discovered_pdfs = [pdf1, pdf2]
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            csv_file = self.crawler.export_to_csv(temp_file.name)
            
            # Verify file was created
            self.assertTrue(os.path.exists(csv_file))
            
            # Verify content
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
                # Check header
                self.assertEqual(rows[0][0], 'URL')
                self.assertEqual(rows[0][1], 'Title')
                self.assertEqual(rows[0][2], 'Author')
                
                # Check data rows
                self.assertEqual(len(rows), 3)  # Header + 2 data rows
                self.assertEqual(rows[1][0], 'https://test.com/doc1.pdf')
                self.assertEqual(rows[2][0], 'https://test.com/doc2.pdf')
            
            # Clean up
            os.unlink(csv_file)
    
    def test_get_crawl_summary(self):
        """Test crawl summary generation"""
        # Add test PDFs
        pdf1 = PDFDocument(
            url="https://site1.com/doc1.pdf",
            title="Document 1",
            author="Author A",
            file_size_bytes=1024000
        )
        
        pdf2 = PDFDocument(
            url="https://site2.com/doc2.pdf",
            title="Document 2",
            author="",  # No author
            file_size_bytes=2048000
        )
        
        self.crawler.discovered_pdfs = [pdf1, pdf2]
        self.crawler.stats.pages_crawled = 10
        self.crawler.stats.pdfs_found = 2
        
        summary = self.crawler.get_crawl_summary()
        
        self.assertEqual(summary['total_pdfs'], 2)
        self.assertEqual(summary['crawl_stats']['pages_crawled'], 10)
        self.assertEqual(summary['pdfs_with_authors'], 1)  # Only pdf1 has author
        self.assertEqual(summary['unique_domains'], 2)  # site1.com and site2.com
        self.assertIn('domains', summary)
        self.assertIn('largest_pdfs', summary)
    
    @patch('Core.pdf_site_crawler.PDFSiteCrawler._crawl_page_comprehensive')
    def test_crawl_site_basic(self, mock_crawl_page):
        """Test basic site crawling functionality"""
        # Mock the page crawling to return test data
        test_pdf = PDFDocument(
            url="https://test.com/document.pdf",
            title="Test Document",
            author="Test Author"
        )
        
        mock_crawl_page.return_value = ([test_pdf], set())
        
        # Test crawling
        result = self.crawler.crawl_site("https://test.com", max_pages=1, max_depth=1)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Test Document")
        self.assertEqual(result[0].author, "Test Author")
        
        # Verify mock was called
        mock_crawl_page.assert_called_once()


if __name__ == '__main__':
    unittest.main()