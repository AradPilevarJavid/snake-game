"""Manifest parsing, validation, fetching, and differential update planning."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
import time
from typing import Callable
import urllib.error
from urllib.parse import urlparse
import urllib.request

from hashing import file_matches
from updater_errors import ManifestError
from version import Version


MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_FILES = 20_000
MAX_TOTAL_SIZE = 4 * 1024 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
RESERVED_ROOTS = {
    "launcher.exe",
    "launcher-config.json",
    "active.json",
    "data",
    "logs",
    ".update",
    "versions",
}


@dataclass(frozen=True)
class FileRecord:
    sha256: str
    size: int


@dataclass(frozen=True)
class Manifest:
    schema_version: int
    version: Version
    channel: str
    update_mode: str
    minimum_supported_version: Version | None
    release_notes: str
    entrypoint: str
    files: dict[str, FileRecord]

    @classmethod
    def from_bytes(cls, payload: bytes) -> "Manifest":
        if len(payload) > MAX_MANIFEST_BYTES:
            raise ManifestError("Update manifest is too large.")
        try:
            raw = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ManifestError("Update manifest is not valid UTF-8 JSON.") from error
        if not isinstance(raw, dict):
            raise ManifestError("Update manifest must be a JSON object.")
        if raw.get("schema_version") != 1:
            raise ManifestError("Unsupported update manifest schema.")

        try:
            version = Version.parse(raw["version"])
        except (KeyError, TypeError, ValueError) as error:
            raise ManifestError("Manifest version is invalid.") from error

        channel = raw.get("channel", "stable")
        update_mode = raw.get("update_mode", "optional")
        release_notes = raw.get("release_notes", "")
        entrypoint = raw.get("entrypoint", "Snake.exe")
        if not isinstance(channel, str) or not channel:
            raise ManifestError("Manifest channel is invalid.")
        if update_mode not in {"optional", "mandatory"}:
            raise ManifestError("Manifest update_mode must be optional or mandatory.")
        if not isinstance(release_notes, str) or len(release_notes) > 100_000:
            raise ManifestError("Manifest release notes are invalid.")

        minimum_raw = raw.get("minimum_supported_version")
        try:
            minimum = Version.parse(minimum_raw) if minimum_raw else None
        except (TypeError, ValueError) as error:
            raise ManifestError("Minimum supported version is invalid.") from error

        raw_files = raw.get("files")
        if not isinstance(raw_files, dict) or not raw_files:
            raise ManifestError("Manifest must contain at least one file.")
        if len(raw_files) > MAX_FILES:
            raise ManifestError("Manifest contains too many files.")

        files: dict[str, FileRecord] = {}
        casefolded_paths: set[str] = set()
        total_size = 0
        for raw_path, raw_record in raw_files.items():
            path = validate_manifest_path(raw_path)
            folded = path.casefold()
            if folded in casefolded_paths:
                raise ManifestError(f"Manifest contains a Windows path collision: {path}")
            casefolded_paths.add(folded)
            if not isinstance(raw_record, dict):
                raise ManifestError(f"Invalid file record for {path}.")
            digest = raw_record.get("sha256", raw_record.get("hash"))
            size = raw_record.get("size")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest.lower()):
                raise ManifestError(f"Invalid SHA-256 for {path}.")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise ManifestError(f"Invalid size for {path}.")
            total_size += size
            if total_size > MAX_TOTAL_SIZE:
                raise ManifestError("Update payload exceeds the allowed size.")
            files[path] = FileRecord(digest.lower(), size)

        entrypoint = validate_manifest_path(entrypoint)
        if entrypoint not in files:
            raise ManifestError("Manifest entrypoint is not included in files.")
        return cls(
            schema_version=1,
            version=version,
            channel=channel,
            update_mode=update_mode,
            minimum_supported_version=minimum,
            release_notes=release_notes,
            entrypoint=entrypoint,
            files=files,
        )

    @property
    def is_mandatory(self) -> bool:
        return self.update_mode == "mandatory"


@dataclass(frozen=True)
class UpdatePlan:
    manifest: Manifest
    reusable: tuple[str, ...]
    downloads: tuple[str, ...]

    @property
    def download_bytes(self) -> int:
        return sum(self.manifest.files[path].size for path in self.downloads)


def validate_manifest_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ManifestError("Manifest contains an invalid file path.")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ManifestError(f"Unsafe manifest path: {value!r}")
    pure_path = PurePosixPath(value)
    if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
        raise ManifestError(f"Unsafe manifest path: {value!r}")
    if pure_path.parts[0].casefold() in RESERVED_ROOTS:
        raise ManifestError(f"Manifest path targets launcher-managed data: {value!r}")
    for part in pure_path.parts:
        if part.endswith((" ", ".")):
            raise ManifestError(f"Windows-incompatible manifest path: {value!r}")
        stem = part.split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED_NAMES:
            raise ManifestError(f"Windows-reserved manifest path: {value!r}")
    return pure_path.as_posix()


class UpdateChecker:
    def __init__(
        self,
        manifest_url: str,
        channel: str = "stable",
        timeout: float = 8.0,
        retries: int = 3,
        opener: Callable[..., object] = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.manifest_url = manifest_url
        self.channel = channel
        self.timeout = timeout
        self.retries = retries
        self.opener = opener
        self.sleeper = sleeper

    def fetch_manifest(self) -> Manifest:
        if not self.manifest_url.lower().startswith("https://"):
            raise ManifestError("Update manifest URL must use HTTPS.")
        original_origin = urlparse(self.manifest_url).netloc.casefold()
        last_error: Exception | None = None
        payload = b""
        for attempt in range(self.retries):
            request = urllib.request.Request(
                self.manifest_url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "SnakeLauncher/1",
                    "Cache-Control": "no-cache",
                },
            )
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    final_url = response.geturl()
                    parsed_final = urlparse(final_url)
                    if parsed_final.scheme.lower() != "https":
                        raise ManifestError(
                            "Update server redirected to a non-HTTPS URL."
                        )
                    if parsed_final.netloc.casefold() != original_origin:
                        raise ManifestError(
                            "Update server redirected to a different origin."
                        )
                    payload = response.read(MAX_MANIFEST_BYTES + 1)
                break
            except ManifestError:
                raise
            except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
                last_error = error
                retryable = not isinstance(error, urllib.error.HTTPError) or error.code in {
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                }
                if not retryable or attempt + 1 >= self.retries:
                    raise ManifestError(
                        f"Could not contact update server: {error}"
                    ) from error
                self.sleeper(min(4.0, 2**attempt))
        if not payload and last_error:
            raise ManifestError(f"Could not contact update server: {last_error}")
        manifest = Manifest.from_bytes(payload)
        if manifest.channel != self.channel:
            raise ManifestError(
                f"Server returned channel {manifest.channel!r}, expected {self.channel!r}."
            )
        return manifest

    @staticmethod
    def plan(manifest: Manifest, active_dir: str | Path | None) -> UpdatePlan:
        active = Path(active_dir) if active_dir else None
        reusable: list[str] = []
        downloads: list[str] = []
        for path, record in manifest.files.items():
            candidate = active.joinpath(*PurePosixPath(path).parts) if active else None
            if candidate and file_matches(candidate, record.sha256, record.size):
                reusable.append(path)
            else:
                downloads.append(path)
        return UpdatePlan(manifest, tuple(reusable), tuple(downloads))
