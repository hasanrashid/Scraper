#!/usr/bin/env python3
"""
Command-line book downloader script for CSV-based book collections.

Usage:
    python download_from_banglabook_csv.py <csv_file> <output_folder> [--limit N]

Examples:
    # Download all books from CSV to output folder
    python download_from_banglabook_csv.py Banglabook-v2/wordpress_scrape.csv Books/Banglabooks-v2

    # Download with limit
    python download_from_banglabook_csv.py Banglabook-v2/wordpress_scrape.csv Books/MyBooks --limit 50

    # Download with absolute paths
    python download_from_banglabook_csv.py /path/to/file.csv /path/to/output

Features:
    - Filters downloads to allowed hosting services only
    - Downloads all valid links (configurable limit)
    - Creates detailed logs in output folder
    - Intelligent book naming: Bengali title -> English title -> URL filename
    - Supports multiple CSV formats
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional
from urllib.parse import urlparse

# Add project root so Core imports work when script is run from elsewhere.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Core.downloader import Downloader

ALLOWED_HOSTS = {
    "drive.google.com",
    "mega.nz",
    "mediafire.com",
    "www.mediafire.com",
    "box.com",
    "www.box.com",
    "app.box.com",
    "dropbox.com",
    "www.dropbox.com",
    "onedrive.live.com",
    "1drv.ms",
    "www.datafilehost.com",
    "datafilehost.com",
    "eboi.org",
}

BLOCKED_HOST_PATTERNS = {
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "pinterest.com",
    "t.me",
    "telegram.me",
    "youtube.com",
    "youtu.be",
}


@dataclass
class Summary:
    total_rows: int = 0
    processed: int = 0
    successful: int = 0
    errors: int = 0
    skipped: int = 0


def setup_logger(output_folder: Path, verbose: bool = False) -> logging.Logger:
    logs_dir = output_folder / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger = logging.getLogger("banglabook_csv_downloader")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    stream_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.info("Book Downloader - CSV to Downloads")
    logger.info("Log file: %s", log_file)
    return logger


def _pick(row: Dict[str, str], *keys: str) -> str:
    for key in keys:
        if key in row and row[key] and row[key].strip():
            return row[key].strip()
    return ""


def sanitize_filename(name: str, fallback: str = "book") -> str:
    name = (name or "").strip()
    if not name:
        name = fallback

    name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = fallback

    # Keep names manageable on common filesystems.
    return name[:160]


def is_allowed_download_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().strip()
        if not host:
            return False

        if host in ALLOWED_HOSTS:
            return True

        # Allow exact subdomain matches of known hosts.
        for allowed in ALLOWED_HOSTS:
            if host.endswith("." + allowed):
                return True

        return False
    except Exception:
        return False


def is_blocked_social_url(url: str) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower().strip()
        if not host:
            return False
        return any(host == x or host.endswith("." + x) for x in BLOCKED_HOST_PATTERNS)
    except Exception:
        return False


def filename_from_row(row: Dict[str, str], url: str) -> str:
    bn_title = _pick(row, "bengali_book_title", "book_title_bn", "book_title_bangla", "title_bn")
    bn_author = _pick(row, "bengali_author", "author_bn")
    en_title = _pick(row, "english_book_title", "book_title_en", "title_en", "title")
    en_author = _pick(row, "english_author", "author_en", "author")

    if bn_title:
        if bn_author:
            return sanitize_filename(f"{bn_title} - {bn_author}")
        return sanitize_filename(bn_title)

    if en_title:
        if en_author:
            return sanitize_filename(f"{en_title} - {en_author}")
        return sanitize_filename(en_title)

    path_name = Path(urlparse(url).path).name
    if path_name:
        return sanitize_filename(path_name)

    return sanitize_filename("downloaded_book")


def iter_csv_rows(csv_file: Path) -> Iterable[Dict[str, str]]:
    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row:
                yield row


def extract_url(row: Dict[str, str]) -> str:
    return _pick(row, "download_url", "download_link", "url", "link", "file_url")


def download_from_csv(csv_file: Path, output_folder: Path, limit: Optional[int], verbose: bool) -> int:
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}")
        return 1

    output_folder.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(output_folder, verbose=verbose)
    summary = Summary()

    logger.info("CSV file: %s", csv_file)
    logger.info("Output folder: %s", output_folder)
    logger.info("Limit: %s", limit if limit is not None else "all")

    rows = list(iter_csv_rows(csv_file))
    summary.total_rows = len(rows)
    if limit is not None:
        rows = rows[:limit]

    logger.info("Processing %d book entries...", len(rows))

    with Downloader(custom_download_folder=str(output_folder)) as downloader:
        for idx, row in enumerate(rows, start=1):
            summary.processed += 1
            url = extract_url(row)
            if not url:
                summary.skipped += 1
                logger.warning("[%d/%d] Skipped row: missing download URL", idx, len(rows))
                continue

            if is_blocked_social_url(url):
                summary.skipped += 1
                logger.warning("[%d/%d] Skipped social/non-download URL: %s", idx, len(rows), url)
                continue

            if not is_allowed_download_url(url):
                summary.skipped += 1
                logger.warning("[%d/%d] Skipped unsupported host URL: %s", idx, len(rows), url)
                continue

            book_title = filename_from_row(row, url)
            logger.info("[%d/%d] Downloading: %s", idx, len(rows), book_title)

            try:
                result = downloader.download_file(url, book_title=book_title)
                if result:
                    summary.successful += 1
                    filename, size = result
                    logger.info("  Successful: %s (%.2f MB)", filename, size / (1024 * 1024))
                else:
                    # Downloader returns None for already-existing files and known non-fatal skips.
                    summary.skipped += 1
                    logger.info("  Skipped/Not downloaded: %s", book_title)
            except Exception as exc:
                summary.errors += 1
                logger.exception("  Error downloading %s: %s", book_title, exc)

    logger.info("Download Summary:")
    logger.info("  Total rows in CSV: %d", summary.total_rows)
    logger.info("  Total processed: %d", summary.processed)
    logger.info("  Successful: %d", summary.successful)
    logger.info("  Errors: %d", summary.errors)
    logger.info("  Skipped: %d", summary.skipped)

    # Return non-zero only for hard errors (not skips).
    return 1 if summary.errors > 0 else 0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download books from a CSV using project downloader strategies")
    parser.add_argument("csv_file", help="Path to CSV file")
    parser.add_argument("output_folder", help="Folder to write downloads")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Maximum rows to process")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    csv_file = Path(args.csv_file).expanduser().resolve()
    output_folder = Path(args.output_folder).expanduser().resolve()

    try:
        return download_from_csv(csv_file, output_folder, args.limit, args.verbose)
    except KeyboardInterrupt:
        print("Interrupted by user")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
