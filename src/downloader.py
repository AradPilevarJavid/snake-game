"""HTTPS downloader with retries, resumable partial files, and hash checks."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import random
import time
import urllib.error
from urllib.parse import urlparse
import urllib.request

from hashing import sha256_file
from updater_errors import DownloadError


ProgressCallback = Callable[[int], None]


class Downloader:
    def __init__(
        self,
        timeout: float = 20.0,
        retries: int = 4,
        chunk_size: int = 256 * 1024,
        opener: Callable[..., object] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.chunk_size = chunk_size
        self.opener = opener
        self.sleeper = sleeper

    def download(
        self,
        url: str,
        destination: str | Path,
        expected_sha256: str,
        expected_size: int,
        progress: ProgressCallback | None = None,
    ) -> Path:
        if not url.lower().startswith("https://"):
            raise DownloadError("Update payload URL must use HTTPS.")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".part")

        last_error: Exception | None = None
        attempts_made = 0
        for attempt in range(self.retries):
            attempts_made = attempt + 1
            try:
                self._download_attempt(
                    url, partial, expected_size, progress or (lambda _count: None)
                )
                if partial.stat().st_size != expected_size:
                    raise DownloadError("Downloaded file has an unexpected size.")
                if sha256_file(partial) != expected_sha256.lower():
                    partial.unlink(missing_ok=True)
                    raise DownloadError("Downloaded file failed SHA-256 verification.")
                os.replace(partial, destination)
                return destination
            except (OSError, urllib.error.URLError, urllib.error.HTTPError, DownloadError) as error:
                last_error = error
                if isinstance(error, urllib.error.HTTPError) and error.code not in {
                    408,
                    416,
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    break
                if attempt + 1 < self.retries:
                    self.sleeper(min(8.0, (2**attempt) + random.random()))
        raise DownloadError(
            f"Download failed after {attempts_made} attempts: {last_error}"
        )

    def _download_attempt(
        self,
        url: str,
        partial: Path,
        expected_size: int,
        progress: ProgressCallback,
    ) -> None:
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > expected_size:
            partial.unlink()
            offset = 0
        headers = {"User-Agent": "SnakeLauncher/1", "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(url, headers=headers)
        try:
            response_context = self.opener(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            if error.code == 416 and offset == expected_size:
                return
            raise

        with response_context as response:
            final_url = response.geturl()
            parsed_original = urlparse(url)
            parsed_final = urlparse(final_url)
            if parsed_final.scheme.lower() != "https":
                raise DownloadError("Payload redirected to a non-HTTPS URL.")
            if parsed_final.netloc.casefold() != parsed_original.netloc.casefold():
                raise DownloadError("Payload redirected to a different origin.")
            status = getattr(response, "status", response.getcode())
            if offset and status != 206:
                offset = 0
                partial.unlink(missing_ok=True)
            if offset and status == 206:
                content_range = response.headers.get("Content-Range", "")
                if not content_range.startswith(f"bytes {offset}-"):
                    raise DownloadError("Server returned an invalid resume range.")

            mode = "ab" if offset and status == 206 else "wb"
            current_size = offset if mode == "ab" else 0
            with partial.open(mode) as file_handle:
                while chunk := response.read(self.chunk_size):
                    current_size += len(chunk)
                    if current_size > expected_size:
                        raise DownloadError("Server sent more data than declared.")
                    file_handle.write(chunk)
                    progress(len(chunk))
                file_handle.flush()
                os.fsync(file_handle.fileno())
