#!/usr/bin/env python3
"""
Generic Blogger Scraper (consolidated)
- Supports WordPress/Atom feed API and sitemap.xml (including sitemap index)
- Extracts download links, plus title/author guesses (English or Bengali); defaults to "not found" if missing
- Saves progress separately per method under an output folder derived from the site name
"""

import os
import re
import json
import csv
import datetime
import warnings
from typing import List, Dict, Tuple, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress XML parsed as HTML warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from Core import scraper
from Core.config_manager import IniConfigManager
from Core.field_truncator import FieldTruncator


class BloggerScraper:
    def __init__(self, site_url: str, site_name: Optional[str] = None, output_dir: Optional[str] = None):
        self.cfg = IniConfigManager()
        self.scraper = scraper.Scraper(self.cfg)
        self.set_site(site_url, site_name, output_dir)
        self.load_download_patterns()

    # --- Configuration helpers ---
    def set_site(self, site_url: str, site_name: Optional[str] = None, output_dir: Optional[str] = None) -> None:
        self.site_url = site_url.rstrip('/') + '/'
        parsed = urlparse(self.site_url)
        base_name = site_name or (parsed.netloc or self.site_url)
        safe_name = re.sub(r"[^A-Za-z0-9]+", "-", base_name).strip('-') or "site"
        self.site_label = safe_name
        self.output_dir = output_dir or f"{safe_name} Scraper"
        os.makedirs(self.output_dir, exist_ok=True)
        self.feed_url = urljoin(self.site_url, "feeds/posts/default")
        self.wordpress_api_url = urljoin(self.site_url, "wp-json/wp/v2/posts")
        self.sitemap_url = urljoin(self.site_url, "sitemap.xml")
        self.site_type = None  # Will be detected on first API call

    def load_download_patterns(self) -> None:
        try:
            mapping_file = os.path.join('Configuration', 'expression-mapping.json')
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            download_urls = mapping.get('Download URL', {})
            self.allowed_hosts = list(download_urls.keys())
            self.file_extensions = mapping.get('File Extensions', ['pdf', 'rar'])
        except Exception:
            self.allowed_hosts = [
                'drive.google.com', 'mediafire.com', 'www.mediafire.com',
                'mega.nz', 'archive.org', 'datafilehost.com', 'www.datafilehost.com',
                'goo.gl', 'bit.ly', 'box.com', 'www.box.com', '1drv.ms', 'onedrive.live.com'
            ]
            self.file_extensions = ['pdf', 'rar', 'epub', 'mobi']

    # --- Progress helpers ---
    def _progress_path(self, mode: str) -> str:
        return os.path.join(self.output_dir, f"{mode}_crawl_progress.json")

    def _load_progress(self, mode: str) -> Tuple[set, List[Dict]]:
        processed = set()
        scraped = []
        path = self._progress_path(mode)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                processed = set(data.get('processed_urls', []))
                scraped = data.get('scraped_pages', [])
            except Exception:
                pass
        return processed, scraped

    def _save_progress(self, mode: str, processed: set, scraped: List[Dict]) -> None:
        path = self._progress_path(mode)
        # Truncate all page data before saving
        truncated_scraped = [FieldTruncator.truncate_scraped_page(page) for page in scraped]
        payload = {
            'last_updated': datetime.datetime.now().isoformat(),
            'total_pages_processed': len(processed),
            'pages_with_download_links': len([d for d in truncated_scraped if d.get('download_links')]),
            'total_download_links': sum(len(d.get('download_links', [])) for d in truncated_scraped),
            'processed_urls': list(processed),
            'scraped_pages': truncated_scraped
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # --- Post discovery ---
    def _detect_site_type(self) -> str:
        """Detect if site is Blogger or WordPress"""
        # Try WordPress REST API first
        try:
            response = requests.get(self.wordpress_api_url, params={'per_page': 1}, timeout=(10, 60))
            if response.status_code == 200:
                return 'wordpress'
        except:
            pass
        
        # Try Blogger Atom feed
        try:
            response = requests.get(self.feed_url, params={'alt': 'json', 'max-results': 1}, timeout=(10, 60))
            if response.status_code == 200:
                return 'blogger'
        except:
            pass
        
        return 'unknown'
    
    def get_posts_from_wordpress_rest_api(self) -> List[Dict]:
        """Fetch posts from WordPress REST API v2 with NO page limits - gets all posts"""
        print("\n📡 Fetching posts from WordPress REST API v2 (NO PAGE LIMITS)...")
        all_posts: List[Dict] = []
        page = 1
        per_page = 100  # API maximum
        consecutive_empty = 0
        
        while True:
            try:
                # No per_page limit in query - fetch all available pages
                params = {
                    'page': page,
                    'per_page': per_page,
                    'orderby': 'date',
                    'order': 'desc'
                }
                response = requests.get(self.wordpress_api_url, params=params, timeout=10)
                
                if response.status_code == 404:
                    print(f"   ⚠️ API endpoint not found (404)")
                    break
                
                if response.status_code != 200:
                    print(f"   ⚠️ HTTP {response.status_code}, stopping pagination")
                    break
                
                posts = response.json()
                
                # Check if we got any posts
                if isinstance(posts, list):
                    if len(posts) == 0:
                        consecutive_empty += 1
                        if consecutive_empty > 2:
                            print(f"   ✓ Reached end of posts (no results on page {page})")
                            break
                    else:
                        consecutive_empty = 0
                        for post in posts:
                            title = post.get('title', {}).get('rendered', 'Unknown') if isinstance(post.get('title'), dict) else post.get('title', 'Unknown')
                            link = post.get('link', '')
                            published = post.get('date', '')
                            if link:
                                all_posts.append({'title': title, 'link': link, 'published': published})
                        
                        print(f"   ✓ Page {page}: {len(posts)} posts (total: {len(all_posts)})")
                        
                        # Continue to next page regardless of count
                        page += 1
                else:
                    # If response is not a list, it might be an error object
                    print(f"   ⚠️ Unexpected response format on page {page}")
                    break
                    
            except requests.exceptions.Timeout:
                print(f"   ⚠️ Timeout on page {page}, stopping")
                break
            except Exception as exc:
                print(f"   ⚠️ Error on page {page}: {exc}")
                break
        
        print(f"   ✓ Total posts fetched: {len(all_posts)} from {page-1} pages")
        return all_posts
    
    def get_posts_from_wordpress_api(self) -> List[Dict]:
        """Fetch posts from Blogger Atom API"""
        print("\n📡 Fetching posts from Blogger Atom API...")
        all_posts: List[Dict] = []
        start_index = 1
        max_results = 500
        while True:
            params = {'alt': 'json', 'start-index': start_index, 'max-results': max_results}
            try:
                response = requests.get(self.feed_url, params=params, timeout=10)
                if response.status_code != 200:
                    break
                data = response.json()
                entries = data.get('feed', {}).get('entry', [])
                if not entries:
                    break
                for entry in entries:
                    title = entry.get('title', {}).get('$t', 'Unknown')
                    link = next((l['href'] for l in entry.get('link', []) if l.get('rel') == 'alternate'), None)
                    published = entry.get('published', {}).get('$t', '')
                    if link:
                        all_posts.append({'title': title, 'link': link, 'published': published})
                start_index += max_results
            except Exception as exc:
                print(f"   ❌ Error fetching posts: {exc}")
                break
        print(f"   ✅ Total posts from Blogger API: {len(all_posts)}")
        return all_posts

    def get_posts_from_sitemap(self) -> List[Dict]:
        print("\n📡 Fetching posts from sitemap.xml...")
        all_posts: List[Dict] = []
        try:
            response = requests.get(self.sitemap_url, timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to fetch sitemap: HTTP {response.status_code}")
                return []
            soup = BeautifulSoup(response.content, 'xml')
            sitemap_refs = soup.find_all('sitemap')
            if sitemap_refs:
                print(f"   📋 Found {len(sitemap_refs)} sub-sitemaps")
                for idx, sitemap_entry in enumerate(sitemap_refs, 1):
                    loc = sitemap_entry.find('loc')
                    if not loc:
                        continue
                    sub_url = loc.text.strip()
                    print(f"   [{idx}/{len(sitemap_refs)}] Fetching {sub_url}")
                    try:
                        sub_resp = requests.get(sub_url, timeout=10)
                        if sub_resp.status_code != 200:
                            print(f"       ⚠️ Failed HTTP {sub_resp.status_code}")
                            continue
                        sub_soup = BeautifulSoup(sub_resp.content, 'xml')
                        self._collect_urls_from_sitemap(sub_soup, all_posts)
                        print(f"       ✅ Total posts so far: {len(all_posts)}")
                    except Exception as exc:
                        print(f"       ❌ Error fetching sub-sitemap: {exc}")
            else:
                self._collect_urls_from_sitemap(soup, all_posts)
            print(f"   ✅ Total posts from all sitemaps: {len(all_posts)}")
        except Exception as exc:
            print(f"   ❌ Error fetching sitemap: {exc}")
        return all_posts

    @staticmethod
    def _collect_urls_from_sitemap(soup: BeautifulSoup, collector: List[Dict]) -> None:
        urls = soup.find_all('url')
        for url_entry in urls:
            loc = url_entry.find('loc')
            lastmod = url_entry.find('lastmod')
            if not loc:
                continue
            url = loc.text.strip()
            # Skip admin, category, tag, archive pages (works for both Blogger and WordPress)
            skip_patterns = [
                '/wp-admin/', '/wp-includes/', '/wp-content/',
                '/category/', '/tag/', '/author/', '/archive/',
                '/feed/', '/search/', '/page/',
                '?', '#'
            ]
            if any(skip in url for skip in skip_patterns):
                continue
            # Include post/article URLs (Blogger: /20XX/*.html, WordPress: various patterns)
            if url and len(url.strip('/').split('/')) >= 2:
                collector.append({
                    'link': url,
                    'lastmod': lastmod.text.strip() if lastmod else '',
                    'title': 'Unknown'
                })

    # --- Page processing ---
    def find_download_links(self, html_content, base_url: str) -> List[Dict]:
        if not html_content:
            return []
        download_links = []
        seen = set()
        download_cues = ['download', 'read', 'get', 'ডাউনলোড', 'পড়ুন', 'পড়ুন']

        def maybe_add(anchor, context_text=""):
            href = anchor.get('href') if hasattr(anchor, 'get') else None
            if not href:
                return
            full_url = href if href.startswith('http') else urljoin(base_url, href)
            if full_url in seen:
                return
            if any(skip in full_url.lower() for skip in [
                'blogger.com', 'blogspot.com', 'blogger.googleusercontent.com',
                'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
                'linkedin.com', '/search/', '/label/', '#comment',
                'javascript:', 'mailto:'
            ]):
                return
            if not any(host in full_url for host in self.allowed_hosts):
                return
            has_ext = any(full_url.lower().endswith(f'.{ext}') for ext in self.file_extensions)
            link_text = anchor.get_text(strip=True) if hasattr(anchor, 'get_text') else ''
            download_links.append({
                'url': full_url,
                'text': link_text if link_text else '(no text)',
                'title': anchor.get('title', '') if hasattr(anchor, 'get') else '',
                'context': context_text,
                'has_file_extension': has_ext
            })
            seen.add(full_url)

        for element in html_content:
            if not hasattr(element, 'get_text'):
                continue
            text_val = element.get_text(strip=True) or ''
            if any(cue in text_val.lower() for cue in download_cues):
                if hasattr(element, 'find_all'):
                    for a in element.find_all('a'):
                        maybe_add(a, context_text=text_val)
        for element in html_content:
            if hasattr(element, 'get') and element.name == 'a':
                maybe_add(element)
        return download_links

    def extract_title_author(self, html_content) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Heuristic extraction of titles (Bengali/English) and authors from page text."""
        if not html_content:
            return None, None, None, None
        lines: List[str] = []
        for element in html_content:
            if hasattr(element, 'get_text'):
                txt = element.get_text(" ", strip=True)
                if txt:
                    lines.append(txt)

        author = None
        for line in lines:
            m = re.search(r"(?:by|author)[:\-]?\s*(.+)", line, re.IGNORECASE)
            if m:
                author = m.group(1).strip()
                break
            m = re.search(r"(?:লেখক|রচনা|সম্পাদনা)[:\-]?\s*(.+)", line)
            if m:
                author = m.group(1).strip()
                break

        bengali_title = None
        english_title = None
        
        # Detect Bengali characters (Unicode range for Bengali script)
        def is_bengali(text):
            return bool(re.search(r'[\u0980-\u09FF]', text))
        
        for line in lines:
            if 2 <= len(line.split()) <= 20 and len(line) <= 160:
                if is_bengali(line) and not bengali_title:
                    bengali_title = line.strip()
                elif not is_bengali(line) and not english_title:
                    english_title = line.strip()
                if bengali_title and english_title:
                    break

        bengali_author = None
        english_author = None
        if author:
            if is_bengali(author):
                bengali_author = author
            else:
                english_author = author

        return bengali_title, english_title, bengali_author, english_author

    def scrape_page(self, page_url: str):
        try:
            content = self.scraper.get_links(page_url, features='html', links_only=False)
            if not content:
                return None
            links = self.find_download_links(content, page_url)
            bengali_title, english_title, bengali_author, english_author = self.extract_title_author(content)
            if links:
                return {
                    'download_links': links,
                    'download_links_count': len(links),
                    'bengali_title_guess': bengali_title,
                    'english_title_guess': english_title,
                    'bengali_author_guess': bengali_author,
                    'english_author_guess': english_author,
                    'author_guess': english_author or bengali_author
                }
            return None
        except Exception as exc:
            print(f"   ❌ Error scraping {page_url}: {exc}")
            return None

    def _csv_path(self, mode: str, csv_path: Optional[str]) -> str:
        if not csv_path:
            return os.path.join(self.output_dir, f"{mode}_scrape.csv")
        if mode == 'both':
            return csv_path
        base, ext = os.path.splitext(csv_path)
        ext = ext or '.csv'
        return f"{base}-{mode}{ext}"

    def write_csv(self, scraped: List[Dict], csv_path: str) -> None:
        headers = [
            'bengali_book_title',
            'bengali_author',
            'english_book_title',
            'english_author',
            'page_url',
            'download_url',
            'scrape_date'
        ]
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for page in scraped:
                page_url = page.get('post_link', '')
                scrape_date = page.get('scrape_date', '')
                bengali_title = page.get('bengali_title', '')
                english_title = page.get('english_title', '')
                bengali_author = page.get('bengali_author', '')
                english_author = page.get('english_author', '')
                for link in page.get('download_links', []):
                    download_url = link.get('url', '') if isinstance(link, dict) else str(link)
                    # Truncate all fields based on field names
                    row_data = [
                        bengali_title,
                        bengali_author,
                        english_title,
                        english_author,
                        page_url,
                        download_url,
                        scrape_date
                    ]
                    truncated_row = FieldTruncator.truncate_csv_row(row_data, headers)
                    writer.writerow(truncated_row)

    # --- Run modes ---
    def run_wordpress(self, output_format: str = "json", csv_path: Optional[str] = None) -> None:
        # Auto-detect site type on first run
        if not self.site_type:
            print("🔍 Detecting site type (Blogger vs WordPress)...")
            self.site_type = self._detect_site_type()
            print(f"   Detected: {self.site_type.upper()}")
        
        # Fetch posts using appropriate API
        if self.site_type == 'wordpress':
            posts = self.get_posts_from_wordpress_rest_api()
        else:
            posts = self.get_posts_from_wordpress_api()
        
        if not posts:
            print("❌ No posts found")
            return
        processed, scraped = self._load_progress('wordpress')
        print(f"\n📄 Processing {len(posts)} posts via API...")
        processed_pages = 0
        skipped_pages = 0
        for idx, post in enumerate(posts, 1):
            post_url = post['link']
            post_title = post.get('title', 'Unknown')
            post_date = post.get('published', '')
            if post_url in processed:
                skipped_pages += 1
                if skipped_pages <= 5:
                    print(f"[{idx}/{len(posts)}] ⏭️  Skipping (already processed): {post_title}")
                continue
            print(f"\n[{idx}/{len(posts)}] 📝 {post_title}")
            print(f"    🔗 {post_url}")
            page_data = self.scrape_page(post_url)
            if page_data:
                page_data.update({
                    'post_link': post_url,
                    'post_title': post_title or 'not found',
                    'bengali_title': page_data.get('bengali_title_guess') or 'not found',
                    'english_title': page_data.get('english_title_guess') or 'not found',
                    'bengali_author': page_data.get('bengali_author_guess') or 'not found',
                    'english_author': page_data.get('english_author_guess') or 'not found',
                    'author': page_data.get('author_guess') or 'not found',
                    'post_date': post_date,
                    'scrape_date': datetime.datetime.now().isoformat()
                })
                scraped.append(page_data)
                processed_pages += 1
                print(f"    ✅ Found {page_data['download_links_count']} download links")
            processed.add(post_url)
            if processed_pages % 5 == 0:
                if output_format in ("json", "both"):
                    self._save_progress('wordpress', processed, scraped)
        if output_format in ("json", "both"):
            self._save_progress('wordpress', processed, scraped)
        if output_format in ("csv", "both"):
            csv_out = self._csv_path('wordpress', csv_path)
            self.write_csv(scraped, csv_out)
            print(f"🧾 CSV written to {csv_out}")
        print("\n🎉 API scraping completed!")
        print(f"📊 Stats: total {len(posts)}, skipped {skipped_pages}, processed {processed_pages}")

    def run_sitemap(self, output_format: str = "json", csv_path: Optional[str] = None) -> None:
        posts = self.get_posts_from_sitemap()
        if not posts:
            print("❌ No posts found")
            return
        processed, scraped = self._load_progress('sitemap')
        print(f"\n📄 Processing {len(posts)} posts via sitemap...")
        processed_pages = 0
        skipped_pages = 0
        for idx, post in enumerate(posts, 1):
            post_url = post['link']
            post_lastmod = post.get('lastmod', '')
            if post_url in processed:
                skipped_pages += 1
                if skipped_pages <= 5:
                    print(f"[{idx}/{len(posts)}] ⏭️  Skipping (already processed): {post_url}")
                continue
            print(f"\n[{idx}/{len(posts)}] 📝 Scraping post")
            print(f"    🔗 {post_url}")
            page_data = self.scrape_page(post_url)
            if page_data:
                page_data.update({
                    'post_link': post_url,
                    'post_title': 'not found',
                    'bengali_title': page_data.get('bengali_title_guess') or 'not found',
                    'english_title': page_data.get('english_title_guess') or 'not found',
                    'bengali_author': page_data.get('bengali_author_guess') or 'not found',
                    'english_author': page_data.get('english_author_guess') or 'not found',
                    'author': page_data.get('author_guess') or 'not found',
                    'post_date': post_lastmod,
                    'scrape_date': datetime.datetime.now().isoformat()
                })
                scraped.append(page_data)
                processed_pages += 1
                print(f"    ✅ Found {page_data['download_links_count']} download links")
            processed.add(post_url)
            if processed_pages % 5 == 0:
                if output_format in ("json", "both"):
                    self._save_progress('sitemap', processed, scraped)
        if output_format in ("json", "both"):
            self._save_progress('sitemap', processed, scraped)
        if output_format in ("csv", "both"):
            csv_out = self._csv_path('sitemap', csv_path)
            self.write_csv(scraped, csv_out)
            print(f"🧾 CSV written to {csv_out}")
        print("\n🎉 Sitemap scraping completed!")
        print(f"📊 Stats: total {len(posts)}, skipped {skipped_pages}, processed {processed_pages}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Consolidated Blogger scraper (API + sitemap)")
    parser.add_argument("site_url", help="Base site URL, e.g., https://dhulokhela.blogspot.com/")
    parser.add_argument("--site-name", help="Readable site name for output folder", default=None)
    parser.add_argument("--mode", choices=["api", "sitemap", "both"], default="both",
                        help="Scrape via API feed, sitemap, or both")
    parser.add_argument("--output-format", choices=["json", "csv", "both"], default="json",
                        help="Output format: json, csv, or both")
    parser.add_argument("--output-dir", default=None,
                        help="Optional output folder to store JSON/CSV files")
    parser.add_argument("--csv-path", default=None,
                        help="Optional CSV output path. For mode=both, files will be suffixed by mode.")
    args = parser.parse_args()

    scraper_obj = BloggerScraper(args.site_url, args.site_name, output_dir=args.output_dir)
    if args.mode in ("api", "both"):
        scraper_obj.run_wordpress(output_format=args.output_format, csv_path=args.csv_path)
    if args.mode in ("sitemap", "both"):
        scraper_obj.run_sitemap(output_format=args.output_format, csv_path=args.csv_path)
