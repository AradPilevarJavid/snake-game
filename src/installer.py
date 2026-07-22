"""Transactional version-slot installation and atomic activation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import time
from typing import Callable
from urllib.parse import quote
import uuid

from downloader import Downloader
from hashing import file_matches
from update_checker import Manifest, UpdatePlan
from updater_errors import InstallError


@dataclass(frozen=True)
class ActiveRelease:
    version: str
    directory: str
    entrypoint: str

    @classmethod
    def from_path(cls, path: Path) -> "ActiveRelease | None":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            release = cls(raw["version"], raw["directory"], raw["entrypoint"])
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return None
        if release.directory != release.version:
            return None
        return release

    def to_dict(self) -> dict[str, str]:
        return {
            "version": self.version,
            "directory": self.directory,
            "entrypoint": self.entrypoint,
        }


class Installer:
    def __init__(
        self,
        install_root: str | Path,
        payload_base_url: str,
        downloader: Downloader | None = None,
    ) -> None:
        self.root = Path(install_root).resolve()
        self.versions_dir = self.root / "versions"
        self.work_dir = self.root / ".update"
        self.active_path = self.root / "active.json"
        self.payload_base_url = payload_base_url.rstrip("/")
        self.downloader = downloader or Downloader()

    def prepare(self) -> None:
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.recover()

    def recover(self) -> None:
        if not self.work_dir.exists():
            return
        for child in self.work_dir.glob("staging-*"):
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)

    def get_active(self) -> ActiveRelease | None:
        release = ActiveRelease.from_path(self.active_path)
        if not release:
            return None
        release_dir = self.versions_dir / release.directory
        entrypoint = release_dir.joinpath(*PurePosixPath(release.entrypoint).parts)
        try:
            record = self._entrypoint_record(release)
        except InstallError:
            return None
        if not file_matches(entrypoint, *record):
            return None
        return release

    def _entrypoint_record(self, release: ActiveRelease) -> tuple[str, int]:
        manifest_path = self.versions_dir / release.directory / ".installed-manifest.json"
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = raw["files"][release.entrypoint]
            return record["sha256"], record["size"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise InstallError("Active release metadata is damaged.") from error

    def active_directory(self) -> Path | None:
        release = ActiveRelease.from_path(self.active_path)
        if not release:
            return None
        directory = self.versions_dir / release.directory
        return directory if directory.is_dir() else None

    def install(
        self,
        plan: UpdatePlan,
        progress: Callable[[int], None] | None = None,
    ) -> ActiveRelease:
        manifest = plan.manifest
        version_name = str(manifest.version)
        final_dir = self.versions_dir / version_name
        if final_dir.exists():
            self._verify_tree(final_dir, manifest)
            self._write_installed_manifest(final_dir, manifest)
            return ActiveRelease(version_name, version_name, manifest.entrypoint)

        staging = self.work_dir / f"staging-{version_name}-{uuid.uuid4().hex}"
        active_dir = self.active_directory()
        staging.mkdir(parents=True)
        try:
            for path in plan.reusable:
                if not active_dir:
                    raise InstallError("Update plan references a missing active release.")
                source = active_dir.joinpath(*PurePosixPath(path).parts)
                destination = staging.joinpath(*PurePosixPath(path).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.link(source, destination)
                except OSError:
                    shutil.copy2(source, destination)

            for path in plan.downloads:
                record = manifest.files[path]
                destination = staging.joinpath(*PurePosixPath(path).parts)
                encoded_path = "/".join(
                    quote(part, safe="") for part in PurePosixPath(path).parts
                )
                url = (
                    f"{self.payload_base_url}/releases/"
                    f"{quote(version_name, safe='')}/{encoded_path}"
                )
                self.downloader.download(
                    url,
                    destination,
                    record.sha256,
                    record.size,
                    progress=progress,
                )

            self._verify_tree(staging, manifest)
            self._write_installed_manifest(staging, manifest)
            os.replace(staging, final_dir)
            return ActiveRelease(version_name, version_name, manifest.entrypoint)
        except Exception as error:
            shutil.rmtree(staging, ignore_errors=True)
            if isinstance(error, InstallError):
                raise
            raise InstallError(f"Could not stage update: {error}") from error

    def activate(self, release: ActiveRelease) -> ActiveRelease | None:
        previous = ActiveRelease.from_path(self.active_path)
        self._atomic_json_write(self.active_path, release.to_dict())
        return previous

    def rollback(self, previous: ActiveRelease | None) -> None:
        if previous:
            self._atomic_json_write(self.active_path, previous.to_dict())
        else:
            self.active_path.unlink(missing_ok=True)

    def release_executable(self, release: ActiveRelease) -> Path:
        return (self.versions_dir / release.directory).joinpath(
            *PurePosixPath(release.entrypoint).parts
        )

    def cleanup_old_versions(self, keep: set[str]) -> None:
        candidates = sorted(
            (path for path in self.versions_dir.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        retained = len(keep)
        for path in candidates:
            if path.name in keep:
                continue
            if retained < 2:
                retained += 1
                continue
            shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def _verify_tree(directory: Path, manifest: Manifest) -> None:
        for path, record in manifest.files.items():
            candidate = directory.joinpath(*PurePosixPath(path).parts)
            if not file_matches(candidate, record.sha256, record.size):
                raise InstallError(f"Staged file failed verification: {path}")

    @staticmethod
    def _write_installed_manifest(directory: Path, manifest: Manifest) -> None:
        payload = {
            "schema_version": manifest.schema_version,
            "version": str(manifest.version),
            "entrypoint": manifest.entrypoint,
            "files": {
                path: {"sha256": record.sha256, "size": record.size}
                for path, record in manifest.files.items()
            },
        }
        Installer._atomic_json_write(directory / ".installed-manifest.json", payload)

    @staticmethod
    def _atomic_json_write(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as file_handle:
            json.dump(payload, file_handle, indent=2, sort_keys=True)
            file_handle.write("\n")
            file_handle.flush()
            os.fsync(file_handle.fileno())
        os.replace(temporary, path)
