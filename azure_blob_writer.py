#!/usr/bin/env python3
"""
Azure Blob Storage upload / download helper for the scraper Azure Function.

Authentication
--------------
Priority order:
  1. AZURE_STORAGE_CONNECTION_STRING env var  — connection string (dev / staging)
  2. DefaultAzureCredential + AZURE_STORAGE_ACCOUNT_URL  — Managed Identity (prod)

In production on Azure, assign the Function App's Managed Identity the
"Storage Blob Data Contributor" role on the storage account and set only
AZURE_STORAGE_ACCOUNT_URL.  No secrets or keys need to be stored.

Required env vars
-----------------
  One of:
    AZURE_STORAGE_CONNECTION_STRING   e.g. "DefaultEndpointsProtocol=https;..."
    AZURE_STORAGE_ACCOUNT_URL         e.g. "https://<account>.blob.core.windows.net"

  Optional:
    AZURE_STORAGE_CONTAINER_NAME      Container name (default: "scraped-links")
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings


class BlobStorageWriter:
    """Thin wrapper around azure-storage-blob for upload/download operations."""

    def __init__(self) -> None:
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if conn_str:
            self._client = BlobServiceClient.from_connection_string(conn_str)
            logging.debug("BlobStorageWriter: using connection string auth")
        else:
            account_url = os.environ["AZURE_STORAGE_ACCOUNT_URL"]
            # Imported lazily so the package is only required when using MI auth.
            from azure.identity import DefaultAzureCredential  # noqa: PLC0415

            self._client = BlobServiceClient(
                account_url=account_url,
                credential=DefaultAzureCredential(),
            )
            logging.debug(
                "BlobStorageWriter: using DefaultAzureCredential for %s",
                account_url,
            )

        self.container = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scraped-links")
        self._ensure_container()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(
        self,
        blob_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload *data* bytes to *blob_name*, overwriting any existing blob."""
        blob_client = self._client.get_blob_client(self.container, blob_name)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        logging.info(
            "Uploaded blob '%s/%s' (%d bytes)", self.container, blob_name, len(data)
        )

    def download(self, blob_name: str) -> Optional[bytes]:
        """Return the raw bytes of *blob_name*, or ``None`` if it does not exist."""
        try:
            blob_client = self._client.get_blob_client(self.container, blob_name)
            return blob_client.download_blob().readall()
        except ResourceNotFoundError:
            return None
        except Exception as exc:
            logging.warning(
                "Could not download blob '%s/%s': %s", self.container, blob_name, exc
            )
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_container(self) -> None:
        """Create the blob container if it does not already exist."""
        try:
            self._client.create_container(self.container)
            logging.info("Created blob container: %s", self.container)
        except ResourceExistsError:
            pass  # Already exists — fine.
