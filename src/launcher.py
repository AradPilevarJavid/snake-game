"""Stable Windows launcher responsible for checking, installing, and starting Snake."""

from __future__ import annotations

import ctypes
import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time

from downloader import Downloader
from installer import ActiveRelease, Installer
from launcher_config import LauncherConfig
from logging_config import configure_logging
from progress_ui import ProgressWindow, ask_optional_update, show_error
from update_checker import Manifest, UpdateChecker
from updater_errors import ConfigurationError, ManifestError, UpdaterError
from version import Version


MUTEX_NAME = "Local\\SnakeGameLauncher-45E82CF4-18B1-4FCB-A9BE-81E32B411D15"


def install_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


class SingleInstance:
    def __init__(self) -> None:
        self.handle = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        kernel32 = ctypes.windll.kernel32
        self.handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        return bool(self.handle) and kernel32.GetLastError() != 183

    def close(self) -> None:
        if self.handle and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(self.handle)


def launch_game(
    installer: Installer,
    release: ActiveRelease,
    data_dir: Path,
    health_timeout: float | None = None,
) -> bool:
    executable = installer.release_executable(release)
    if not executable.is_file():
        raise UpdaterError(f"Game executable is missing: {executable}")

    environment = os.environ.copy()
    environment["SNAKE_DATA_DIR"] = str(data_dir)
    command = [str(executable)]
    health_file = None
    token = None
    if health_timeout is not None:
        health_dir = installer.work_dir / "health"
        health_dir.mkdir(parents=True, exist_ok=True)
        token = secrets.token_urlsafe(32)
        health_file = health_dir / f"{os.getpid()}-{time.time_ns()}.ready"
        command.extend(
            [
                "--update-health-file",
                str(health_file),
                "--update-health-token",
                token,
            ]
        )

    process = subprocess.Popen(
        command,
        cwd=executable.parent,
        env=environment,
        close_fds=True,
    )
    if health_timeout is None:
        return True

    deadline = time.monotonic() + health_timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            if health_file and health_file.read_text(encoding="utf-8") == token:
                health_file.unlink(missing_ok=True)
                return True
        except OSError:
            pass
        time.sleep(0.2)
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    return False


def current_version(active: ActiveRelease | None) -> Version | None:
    if not active:
        return None
    try:
        return Version.parse(active.version)
    except ValueError:
        return None


def launcher_state_path(root: Path) -> Path:
    return root / "data" / "launcher-state.json"


def load_launcher_state(root: Path) -> dict[str, object]:
    try:
        raw = json.loads(launcher_state_path(root).read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_launcher_state(root: Path, state: dict[str, object]) -> None:
    path = launcher_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def migrate_legacy_data(root: Path, data_dir: Path) -> None:
    destination = data_dir / "scores.json"
    source = root / "scores.json"
    if not destination.exists() and source.is_file():
        try:
            destination.write_bytes(source.read_bytes())
        except OSError:
            pass


def update_is_mandatory(manifest: Manifest, installed: Version | None) -> bool:
    if manifest.is_mandatory:
        return True
    return bool(
        installed
        and manifest.minimum_supported_version
        and installed < manifest.minimum_supported_version
    )


def run_update(
    installer: Installer,
    checker: UpdateChecker,
    manifest: Manifest,
    active: ActiveRelease | None,
    config: LauncherConfig,
    data_dir: Path,
    root: Path,
    logger: logging.Logger,
) -> bool:
    installed = current_version(active)
    mandatory = active is None or update_is_mandatory(manifest, installed)
    current_label = str(installed) if installed else "Not installed"
    if not mandatory and not ask_optional_update(
        current_label, str(manifest.version), manifest.release_notes
    ):
        logger.info("User skipped optional update %s", manifest.version)
        state = load_launcher_state(root)
        state["skipped_version"] = str(manifest.version)
        save_launcher_state(root, state)
        return bool(active and launch_game(installer, active, data_dir))

    plan = checker.plan(manifest, installer.active_directory())
    window = ProgressWindow(current_label, str(manifest.version), plan.download_bytes)
    result: dict[str, object] = {}

    def worker() -> None:
        previous: ActiveRelease | None = None
        try:
            logger.info(
                "Installing %s: %d downloads, %d reusable files",
                manifest.version,
                len(plan.downloads),
                len(plan.reusable),
            )
            release = installer.install(plan, progress=window.add_downloaded)
            window.set_status("Installing...")
            previous = installer.activate(release)
            window.set_status("Launching game...")
            if not launch_game(
                installer,
                release,
                data_dir,
                health_timeout=config.health_timeout_seconds,
            ):
                installer.rollback(previous)
                raise UpdaterError(
                    "The updated game did not start correctly. "
                    "The previous version was restored."
                )
            keep = {release.version}
            if previous:
                keep.add(previous.version)
            installer.cleanup_old_versions(keep)
            state = load_launcher_state(root)
            state.pop("skipped_version", None)
            save_launcher_state(root, state)
            result["success"] = True
            logger.info("Update %s installed successfully", manifest.version)
        except Exception as error:
            if previous:
                installer.rollback(previous)
            result["error"] = error
            logger.exception("Update failed")
        finally:
            window.close()

    threading.Thread(target=worker, daemon=True).start()
    window.run()
    error = result.get("error")
    if error:
        show_error("Update Failed", str(error))
        if active and not mandatory:
            return launch_game(installer, active, data_dir)
        return False
    return bool(result.get("success"))


def main() -> int:
    root = install_root()
    logger = configure_logging(root / "logs")
    instance = SingleInstance()
    if not instance.acquire():
        logger.info("Another launcher instance is already running")
        return 0

    try:
        data_dir = root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        migrate_legacy_data(root, data_dir)
        try:
            config = LauncherConfig.load(root)
        except ConfigurationError as error:
            show_error("Launcher Configuration Error", str(error))
            return 2

        installer = Installer(
            root,
            config.update_base_url,
            Downloader(timeout=config.download_timeout_seconds),
        )
        installer.prepare()
        active = installer.get_active()
        checker = UpdateChecker(
            f"{config.update_base_url}/version.json",
            channel=config.channel,
            timeout=config.check_timeout_seconds,
        )
        try:
            manifest = checker.fetch_manifest()
        except ManifestError as error:
            logger.warning("Update check failed: %s", error)
            if active:
                return 0 if launch_game(installer, active, data_dir) else 1
            show_error(
                "Cannot Start Snake",
                "No installed game is available and the update server could not "
                f"be reached.\n\n{error}",
            )
            return 1

        installed = current_version(active)
        if installed and manifest.version <= installed:
            logger.info("No update available; installed version is %s", installed)
            return 0 if launch_game(installer, active, data_dir) else 1
        state = load_launcher_state(root)
        if (
            active
            and not update_is_mandatory(manifest, installed)
            and state.get("skipped_version") == str(manifest.version)
        ):
            logger.info("Optional update %s was previously skipped", manifest.version)
            return 0 if launch_game(installer, active, data_dir) else 1
        return (
            0
            if run_update(
                installer, checker, manifest, active, config, data_dir, root, logger
            )
            else 1
        )
    except Exception as error:
        logger.exception("Unhandled launcher error")
        show_error("Snake Launcher Error", str(error))
        return 1
    finally:
        instance.close()


if __name__ == "__main__":
    raise SystemExit(main())
