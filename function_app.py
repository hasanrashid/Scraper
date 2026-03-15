#!/usr/bin/env python3
"""
Azure Functions timer-triggered PDF link scraper.

Runs on a configurable CRON schedule (SCRAPER_SCHEDULE app setting).
For each site in SCRAPER_SITES (or sites_config.json), it:
  1. Restores prior crawl progress from Azure Blob Storage so already-scraped
     URLs are skipped on incremental runs.
  2. Calls BloggerScraper to scrape PDF download links via WordPress REST API
     and/or sitemap.xml.
  3. Uploads the resulting CSV (all accumulated rows) and updated progress JSON
     back to Azure Blob Storage.

Required Azure App Settings
---------------------------
SCRAPER_SCHEDULE            CRON expression (6-field Azure format, e.g. "0 0 0 * * *")
SCRAPER_SITES               JSON array of site objects (see sites_config.json for format)
                            If omitted, falls back to sites_config.json in the app directory.

Plus whichever storage settings azure_blob_writer.py requires:
  AZURE_STORAGE_CONNECTION_STRING  — simple connection string (dev / staging)
  OR
  AZURE_STORAGE_ACCOUNT_URL        — e.g. "https://<account>.blob.core.windows.net"
                                     (uses Managed Identity via DefaultAzureCredential)
  AZURE_STORAGE_CONTAINER_NAME     — blob container name (default: "scraped-links")

Blob paths written
------------------
  {site_name}/{YYYY-MM-DD}/wordpress_scrape.csv   — date-stamped CSV snapshot
  {site_name}/{YYYY-MM-DD}/sitemap_scrape.csv
  {site_name}/wordpress_crawl_progress.json       — persistent progress (resume state)
  {site_name}/sitemap_crawl_progress.json
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import azure.functions as func

from azure_blob_writer import BlobStorageWriter
from consolidated_scraper import BloggerScraper
from download_from_banglabook_csv import download_from_csv

app = func.FunctionApp()


@app.timer_trigger(
    schedule="%SCRAPER_SCHEDULE%",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=False,
)
def pdf_link_scraper(timer: func.TimerRequest) -> None:
    """Entry point: runs on schedule, scrapes all configured sites."""
    if timer.past_due:
        logging.warning("Timer is past due — running anyway")

    sites = _load_sites()
    if not sites:
        logging.error(
            "No sites configured. Set the SCRAPER_SITES app setting or "
            "add entries to sites_config.json."
        )
        return

    writer = BlobStorageWriter()
    today = datetime.date.today().isoformat()
    success_count = 0
    error_count = 0

    for site in sites:
        site_url = site.get("url")
        if not site_url:
            logging.warning("Site entry missing 'url', skipping: %s", site)
            continue

        site_name = site.get("name") or _name_from_url(site_url)
        mode = site.get("mode", "sitemap")  # "api" | "sitemap" | "both"

        logging.info(
            "Scraping '%s' (%s, mode=%s)", site_name, site_url, mode
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                scraper = BloggerScraper(
                    site_url=site_url,
                    site_name=site_name,
                    output_dir=tmpdir,
                )

                # Restore persisted progress so the scraper skips already-seen URLs.
                for progress_mode in ("wordpress", "sitemap"):
                    _restore_progress(writer, site_name, progress_mode, tmpdir)

                if mode in ("api", "both"):
                    scraper.run_wordpress(output_format="both", csv_path=None)
                    _upload_artifacts(
                        writer, site_name, "wordpress", tmpdir, today
                    )

                if mode in ("sitemap", "both"):
                    scraper.run_sitemap(output_format="both", csv_path=None)
                    _upload_artifacts(
                        writer, site_name, "sitemap", tmpdir, today
                    )

                success_count += 1
                logging.info("Finished '%s'", site_name)

            except Exception:
                logging.exception("Error scraping '%s'", site_name)
                error_count += 1

    logging.info(
        "Scraper run complete. success=%d errors=%d", success_count, error_count
    )


@app.timer_trigger(
    schedule="%SCRAPER_SCHEDULE%",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=False,
)
def csv_downloader_job(timer: func.TimerRequest) -> None:
    """Optional timer job that runs CSV downloader logic without shell execution.

    Enable with app setting `CSV_DOWNLOADER_ENABLED=true`.
    Jobs are read from JSON app setting `CSV_DOWNLOAD_JOBS`, for example:
      [
        {
          "csv_file": "Banglabook-v2/wordpress_scrape.csv",
          "output_folder": "Books/Banglabooks-v2",
          "limit": 50
        }
      ]

    This uses the same Python function that powers the CLI script.
    """
    if not _is_truthy(os.getenv("CSV_DOWNLOADER_ENABLED", "false")):
        logging.info("CSV downloader job disabled (CSV_DOWNLOADER_ENABLED != true)")
        return

    if timer.past_due:
        logging.warning("CSV downloader timer is past due - running anyway")

    jobs = _load_csv_download_jobs()
    if not jobs:
        logging.warning("CSV downloader enabled but CSV_DOWNLOAD_JOBS is empty")
        return

    ok_count = 0
    err_count = 0

    for idx, job in enumerate(jobs, start=1):
        csv_path_raw = (job.get("csv_file") or "").strip()
        out_path_raw = (job.get("output_folder") or "").strip()
        limit = job.get("limit")
        verbose = bool(job.get("verbose", False))

        if not csv_path_raw or not out_path_raw:
            logging.error(
                "CSV job %d missing csv_file/output_folder: %s", idx, job
            )
            err_count += 1
            continue

        csv_path = Path(csv_path_raw)
        output_folder = Path(out_path_raw)

        if not csv_path.is_absolute():
            csv_path = Path(__file__).parent / csv_path
        if not output_folder.is_absolute():
            output_folder = Path(__file__).parent / output_folder

        logging.info(
            "CSV job %d: csv=%s out=%s limit=%s",
            idx,
            csv_path,
            output_folder,
            limit,
        )

        try:
            code = download_from_csv(
                csv_file=csv_path,
                output_folder=output_folder,
                limit=limit,
                verbose=verbose,
            )
            if code == 0:
                ok_count += 1
            else:
                err_count += 1
        except Exception:
            logging.exception("CSV job %d failed", idx)
            err_count += 1

    logging.info("CSV downloader run complete. success=%d errors=%d", ok_count, err_count)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_sites() -> list[dict]:
    """Load site list from SCRAPER_SITES env var or local sites_config.json."""
    env_value = os.getenv("SCRAPER_SITES")
    if env_value:
        try:
            return json.loads(env_value)
        except json.JSONDecodeError:
            logging.error("SCRAPER_SITES is not valid JSON")
            return []

    config_path = os.path.join(os.path.dirname(__file__), "sites_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("sites", [])

    return []


def _load_csv_download_jobs() -> list[dict]:
    """Load CSV downloader jobs from CSV_DOWNLOAD_JOBS JSON app setting."""
    raw = os.getenv("CSV_DOWNLOAD_JOBS", "").strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logging.error("CSV_DOWNLOAD_JOBS is not valid JSON")
        return []

    if not isinstance(data, list):
        logging.error("CSV_DOWNLOAD_JOBS must be a JSON array")
        return []

    # Keep only object entries.
    return [x for x in data if isinstance(x, dict)]


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _name_from_url(url: str) -> str:
    host = urlparse(url).netloc or url
    return host.replace(".", "-").strip("-") or "site"


def _restore_progress(
    writer: BlobStorageWriter,
    site_name: str,
    mode: str,
    tmpdir: str,
) -> None:
    """Download persisted crawl progress JSON from blob and write it to tmpdir.

    BloggerScraper._load_progress() reads from tmpdir, so this causes it to
    skip previously processed URLs on the next run.
    """
    blob_name = f"{site_name}/{mode}_crawl_progress.json"
    data = writer.download(blob_name)
    if data:
        local_path = os.path.join(tmpdir, f"{mode}_crawl_progress.json")
        with open(local_path, "wb") as f:
            f.write(data)
        logging.info("Restored progress for %s/%s", site_name, mode)


def _upload_artifacts(
    writer: BlobStorageWriter,
    site_name: str,
    mode: str,
    tmpdir: str,
    today: str,
) -> None:
    """Upload the scrape CSV and updated progress JSON produced by a single mode run."""
    # CSV → date-stamped path so every run is preserved.
    csv_local = os.path.join(tmpdir, f"{mode}_scrape.csv")
    if os.path.exists(csv_local):
        with open(csv_local, "rb") as f:
            writer.upload(
                f"{site_name}/{today}/{mode}_scrape.csv",
                f.read(),
                content_type="text/csv; charset=utf-8",
            )
    else:
        logging.warning("No CSV output found for %s/%s", site_name, mode)

    # Progress JSON → fixed path (overwritten) so incremental runs resume.
    progress_local = os.path.join(tmpdir, f"{mode}_crawl_progress.json")
    if os.path.exists(progress_local):
        with open(progress_local, "rb") as f:
            writer.upload(
                f"{site_name}/{mode}_crawl_progress.json",
                f.read(),
                content_type="application/json",
            )
