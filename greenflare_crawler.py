#!/usr/bin/env python3
"""
GreenFlare-like PDF Site Crawler
Comprehensive website crawler for discovering all PDF documents with title and author extraction
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Core.config_manager import IniConfigManager
from Core.http_client import RequestsHttpClient
from Core.scraper import Scraper
from Core.pdf_site_crawler import PDFSiteCrawler


def main():
    """Main function for comprehensive PDF site crawling"""
    
    parser = argparse.ArgumentParser(description='Crawl entire website for PDF documents')
    parser.add_argument('url', help='Website URL to crawl')
    parser.add_argument('--max-pages', type=int, help='Maximum pages to crawl')
    parser.add_argument('--max-depth', type=int, help='Maximum crawl depth')
    parser.add_argument('--follow-external', action='store_true', help='Follow external links')
    parser.add_argument('--output', help='Output CSV file path')
    parser.add_argument('--delay', type=float, help='Delay between requests (seconds)')
    
    args = parser.parse_args()
    
    print("🌐 GreenFlare-like PDF Site Crawler")
    print("=" * 50)
    print(f"Target URL: {args.url}")
    
    try:
        # Initialize components
        print("\n📋 Initializing crawler components...")
        config_manager = IniConfigManager()
        http_client = RequestsHttpClient(config_manager.get_user_agent())
        scraper = Scraper(config_manager, http_client)
        site_crawler = PDFSiteCrawler(config_manager, http_client, scraper)
        
        # Override config with command line arguments if provided
        crawl_args = {}
        if args.max_pages:
            crawl_args['max_pages'] = args.max_pages
        if args.max_depth:
            crawl_args['max_depth'] = args.max_depth
        if args.follow_external:
            crawl_args['follow_external'] = args.follow_external
        
        print(f"\n🔍 Starting comprehensive site crawl...")
        if crawl_args:
            print(f"Custom settings: {crawl_args}")
        
        # Start the comprehensive crawl
        discovered_pdfs = site_crawler.crawl_site(args.url, **crawl_args)
        
        print(f"\n✅ Crawl completed!")
        
        if discovered_pdfs:
            print(f"\n📚 Found {len(discovered_pdfs)} PDF documents:")
            
            # Show summary of discovered PDFs
            for i, pdf in enumerate(discovered_pdfs[:10], 1):  # Show first 10
                print(f"\n{i}. {pdf.title or 'Untitled'}")
                print(f"   📄 URL: {pdf.url}")
                if pdf.author:
                    print(f"   👤 Author: {pdf.author}")
                if pdf.file_size_mb > 0:
                    print(f"   📊 Size: {pdf.file_size_mb:.2f} MB")
                print(f"   🌐 Found on: {pdf.discovered_on_page}")
                if pdf.link_text:
                    print(f"   🔗 Link text: {pdf.link_text[:100]}{'...' if len(pdf.link_text) > 100 else ''}")
            
            if len(discovered_pdfs) > 10:
                print(f"\n... and {len(discovered_pdfs) - 10} more PDFs")
            
            # Export to CSV
            output_file = args.output if args.output else site_crawler.csv_output
            csv_file = site_crawler.export_to_csv(output_file)
            print(f"\n💾 Exported all PDFs to: {csv_file}")
            
            # Show comprehensive statistics
            summary = site_crawler.get_crawl_summary()
            print(f"\n📊 Crawl Statistics:")
            print(f"   🏃 Duration: {summary['crawl_stats']['duration_seconds']:.1f} seconds")
            print(f"   📄 Pages crawled: {summary['crawl_stats']['pages_crawled']}")
            print(f"   ⚡ Pages/second: {summary['crawl_stats']['pages_per_second']:.2f}")
            print(f"   📚 PDFs found: {summary['total_pdfs']}")
            print(f"   💽 Total size: {summary['total_size_mb']:.2f} MB")
            print(f"   📝 PDFs with authors: {summary['pdfs_with_authors']}")
            print(f"   🌐 Unique domains: {summary['unique_domains']}")
            
            if summary['crawl_stats']['errors_encountered'] > 0:
                print(f"   ❌ Errors: {summary['crawl_stats']['errors_encountered']}")
            
            # Show domain distribution
            if summary['domains']:
                print(f"\n🌐 PDFs by domain:")
                for domain, count in sorted(summary['domains'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"   {domain}: {count} PDFs")
            
            # Show largest PDFs
            if summary['largest_pdfs']:
                print(f"\n📊 Largest PDFs:")
                for title, size_mb, url in summary['largest_pdfs'][:5]:
                    print(f"   {size_mb:.2f} MB - {title}")
            
            print(f"\n🎯 All PDF metadata has been saved to: {csv_file}")
            print("   Columns: URL, Title, Author, File Size, Content Type, Discovery Date, etc.")
        
        else:
            print("❌ No PDF documents found on this website.")
            print("   Try a website that contains research papers, documentation, or ebooks.")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Crawl interrupted by user")
        return 1
    
    except Exception as e:
        print(f"\n❌ Error during crawling: {str(e)}")
        print("Please check the logs for more details.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())