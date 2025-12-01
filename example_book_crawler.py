#!/usr/bin/env python3
"""
PDF Book Crawler Example
Demonstrates how to use the PDF Book Crawler to find books on a website
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Core.config_manager import IniConfigManager
from Core.http_client import RequestsHttpClient
from Core.scraper import Scraper
from Core.pdf_book_crawler import PDFBookCrawler


def main():
    """Main function to demonstrate PDF book crawling"""
    
    # Initialize components
    print("Initializing PDF Book Crawler...")
    config_manager = IniConfigManager()
    http_client = RequestsHttpClient(config_manager.get_user_agent())
    scraper = Scraper(config_manager, http_client)
    book_crawler = PDFBookCrawler(config_manager, http_client, scraper)
    
    # Example website to crawl (replace with actual site)
    start_url = input("Enter the website URL to crawl for PDF books: ").strip()
    
    if not start_url:
        print("No URL provided. Using example URL...")
        start_url = "https://example.com"
    
    print(f"Starting book discovery crawl from: {start_url}")
    print("This may take a few minutes depending on the website size...")
    
    try:
        # Crawl for books
        discovered_books = book_crawler.crawl_for_books(
            start_url=start_url,
            max_depth=3,      # Crawl up to 3 levels deep
            max_pages=50      # Visit up to 50 pages
        )
        
        print(f"\n✅ Book discovery completed!")
        
        if discovered_books:
            print(f"Found {len(discovered_books)} potential books:")
            
            # Show top 5 highest confidence books
            top_books = sorted(discovered_books, 
                             key=lambda x: x.confidence_score, reverse=True)[:5]
            
            print("\n📚 Top discovered books:")
            for i, book in enumerate(top_books, 1):
                print(f"\n{i}. {book.title}")
                print(f"   Author: {book.author}")
                print(f"   Website: {book.website_name}")
                print(f"   File Size: {book.file_size_mb:.2f} MB")
                print(f"   Confidence: {book.confidence_score:.2f}")
                print(f"   URL: {book.source_url}")
            
            # Export to CSV
            csv_file = book_crawler.export_books_to_csv()
            print(f"\n📄 All books exported to: {csv_file}")
            
            # Show summary statistics
            summary = book_crawler.get_discovery_summary()
            print(f"\n📊 Discovery Summary:")
            print(f"   Total books found: {summary['total_books']}")
            print(f"   Average confidence: {summary['average_confidence']}")
            print(f"   Books with authors: {summary['books_with_authors']}")
            print(f"   Books with ISBN: {summary['books_with_isbn']}")
            print(f"   Total size: {summary['total_size_mb']:.2f} MB")
            
            if summary['books_per_website']:
                print(f"\n🌐 Books per website:")
                for website, count in summary['books_per_website'].items():
                    print(f"   {website}: {count} books")
        
        else:
            print("❌ No PDF books found on this website.")
            print("Try with a different website that contains academic papers, ebooks, or documentation.")
    
    except Exception as e:
        print(f"\n❌ Error during crawling: {str(e)}")
        print("Please check the logs for more details.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())