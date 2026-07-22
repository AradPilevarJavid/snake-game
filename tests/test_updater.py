"""Focused unit tests for the launcher's update pipeline."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from downloader import Downloader
from hashing import file_matches, sha256_file
from installer import ActiveRelease, Installer
from update_checker import Manifest, UpdateChecker
from updater_errors import DownloadError, InstallError, ManifestError
from version import Version


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def manifest_bytes(
    files: dict[str, bytes] | None = None,
    *,
    version: str = "1.1.0",
    entrypoint: str = "Snake.exe",
    **overrides: object,
) -> bytes:
    payloads = files or {"Snake.exe": b"new executable"}
    manifest: dict[str, object] = {
        "schema_version": 1,
        "version": version,
        "channel": "stable",
        "update_mode": "optional",
        "minimum_supported_version": None,
        "release_notes": "Bug fixes",
        "entrypoint": entrypoint,
        "files": {
            path: {"sha256": digest(content), "size": len(content)}
            for path, content in payloads.items()
        },
    }
    manifest.update(overrides)
    return json.dumps(manifest).encode("utf-8")


class FakeResponse:
    def __init__(
        self,
        payload: bytes,
        *,
        url: str = "https://updates.example.test/file",
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.stream = io.BytesIO(payload)
        self.url = url
        self.status = status
        self.headers = headers or {}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def geturl(self) -> str:
        return self.url

    def getcode(self) -> int:
        return self.status


class HashingTests(unittest.TestCase):
    def test_sha256_and_file_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "asset.bin"
            candidate.write_bytes(b"snake")

            expected = digest(b"snake")
            self.assertEqual(sha256_file(candidate, chunk_size=2), expected)
            self.assertTrue(file_matches(candidate, expected.upper(), 5))
            self.assertFalse(file_matches(candidate, expected, 4))
            self.assertFalse(file_matches(candidate, "0" * 64, 5))
            self.assertFalse(file_matches(candidate.with_name("missing"), expected, 5))


class VersionTests(unittest.TestCase):
    def test_semantic_version_ordering(self) -> None:
        ordered = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
            "1.0.1",
            "1.1.0",
            "2.0.0",
        ]
        parsed = [Version.parse(item) for item in ordered]

        for earlier, later in zip(parsed, parsed[1:]):
            self.assertLess(earlier, later)
            self.assertGreater(later, earlier)

    def test_parse_accepts_v_prefix_and_ignores_build_metadata_in_string(self) -> None:
        version = Version.parse("v1.2.3-rc.2+windows.1")

        self.assertEqual(str(version), "1.2.3-rc.2")
        self.assertEqual(version, Version.parse("1.2.3-rc.2+other"))

    def test_parse_rejects_non_semantic_versions(self) -> None:
        for value in ("1", "1.2", "01.2.3", "1.2.3.4", "release-1.2.3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Version.parse(value)


class ManifestTests(unittest.TestCase):
    def test_parses_update_policy_and_legacy_hash_key(self) -> None:
        raw = json.loads(manifest_bytes())
        raw["update_mode"] = "mandatory"
        raw["minimum_supported_version"] = "1.0.0"
        record = raw["files"]["Snake.exe"]
        record["hash"] = record.pop("sha256")

        manifest = Manifest.from_bytes(json.dumps(raw).encode())

        self.assertTrue(manifest.is_mandatory)
        self.assertEqual(str(manifest.minimum_supported_version), "1.0.0")
        self.assertEqual(manifest.entrypoint, "Snake.exe")

    def test_rejects_path_traversal_and_windows_unsafe_paths(self) -> None:
        unsafe_paths = (
            "../Snake.exe",
            "assets/../../Snake.exe",
            "/Snake.exe",
            r"assets\Snake.exe",
            "C:/Snake.exe",
            "assets/NUL.txt",
            "assets/trailing.",
            "active.json/Snake.exe",
            ".update/Snake.exe",
        )
        for unsafe_path in unsafe_paths:
            with self.subTest(path=unsafe_path), self.assertRaises(ManifestError):
                Manifest.from_bytes(
                    manifest_bytes(
                        {unsafe_path: b"x"},
                        entrypoint=unsafe_path,
                    )
                )

    def test_rejects_case_insensitive_windows_path_collisions(self) -> None:
        with self.assertRaises(ManifestError):
            Manifest.from_bytes(
                manifest_bytes(
                    {
                        "Snake.exe": b"executable",
                        "assets/Apple.png": b"red",
                        "ASSETS/apple.PNG": b"green",
                    }
                )
            )

    def test_rejects_invalid_file_metadata(self) -> None:
        raw = json.loads(manifest_bytes())
        raw["files"]["Snake.exe"]["sha256"] = "not-a-digest"
        with self.assertRaises(ManifestError):
            Manifest.from_bytes(json.dumps(raw).encode())

        raw = json.loads(manifest_bytes())
        raw["files"]["Snake.exe"]["size"] = True
        with self.assertRaises(ManifestError):
            Manifest.from_bytes(json.dumps(raw).encode())

    def test_requires_entrypoint_to_be_part_of_payload(self) -> None:
        with self.assertRaises(ManifestError):
            Manifest.from_bytes(
                manifest_bytes({"assets/apple.png": b"apple"})
            )


class UpdatePlanningTests(unittest.TestCase):
    def test_plan_reuses_only_exact_local_matches(self) -> None:
        payloads = {
            "Snake.exe": b"new executable",
            "assets/apple.png": b"same apple",
            "assets/font.ttf": b"new font",
        }
        manifest = Manifest.from_bytes(manifest_bytes(payloads))

        with tempfile.TemporaryDirectory() as temporary:
            active = Path(temporary)
            (active / "assets").mkdir()
            (active / "assets/apple.png").write_bytes(payloads["assets/apple.png"])
            (active / "Snake.exe").write_bytes(b"old executable")

            plan = UpdateChecker.plan(manifest, active)

        self.assertEqual(plan.reusable, ("assets/apple.png",))
        self.assertEqual(
            plan.downloads,
            ("Snake.exe", "assets/font.ttf"),
        )
        self.assertEqual(
            plan.download_bytes,
            len(payloads["Snake.exe"]) + len(payloads["assets/font.ttf"]),
        )

    def test_plan_without_active_release_downloads_everything(self) -> None:
        manifest = Manifest.from_bytes(
            manifest_bytes({"Snake.exe": b"exe", "assets/apple.png": b"apple"})
        )

        plan = UpdateChecker.plan(manifest, None)

        self.assertEqual(plan.reusable, ())
        self.assertEqual(plan.downloads, ("Snake.exe", "assets/apple.png"))


class DownloaderTests(unittest.TestCase):
    def test_resumes_partial_download_and_reports_new_bytes(self) -> None:
        payload = b"0123456789"
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse(
                payload[4:],
                status=206,
                headers={"Content-Range": "bytes 4-9/10"},
            )

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "Snake.exe"
            destination.with_name("Snake.exe.part").write_bytes(payload[:4])
            increments: list[int] = []
            downloader = Downloader(
                timeout=3,
                retries=1,
                chunk_size=2,
                opener=opener,
            )

            result = downloader.download(
                "https://updates.example.test/Snake.exe",
                destination,
                digest(payload),
                len(payload),
                progress=increments.append,
            )

            self.assertEqual(result.read_bytes(), payload)
            self.assertFalse(destination.with_name("Snake.exe.part").exists())

        self.assertEqual(requests[0][0].headers["Range"], "bytes=4-")
        self.assertEqual(requests[0][1], 3)
        self.assertEqual(sum(increments), 6)

    def test_restarts_when_server_ignores_range(self) -> None:
        payload = b"complete payload"

        def opener(_request, timeout):
            del timeout
            return FakeResponse(payload, status=200)

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "asset.bin"
            destination.with_name("asset.bin.part").write_bytes(b"partial")

            Downloader(retries=1, opener=opener).download(
                "https://updates.example.test/asset.bin",
                destination,
                digest(payload),
                len(payload),
            )

            self.assertEqual(destination.read_bytes(), payload)

    def test_rejects_insecure_url_and_bad_hash(self) -> None:
        downloader = Downloader(
            retries=1,
            opener=lambda _request, timeout: FakeResponse(b"payload"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "payload.bin"
            with self.assertRaises(DownloadError):
                downloader.download(
                    "http://updates.example.test/payload.bin",
                    destination,
                    digest(b"payload"),
                    7,
                )
            with self.assertRaises(DownloadError):
                downloader.download(
                    "https://updates.example.test/payload.bin",
                    destination,
                    "0" * 64,
                    7,
                )
            self.assertFalse(destination.with_name("payload.bin.part").exists())


class RecordingDownloader:
    def __init__(
        self,
        payloads: dict[str, bytes],
        failure: Exception | None = None,
    ) -> None:
        self.payloads = payloads
        self.failure = failure
        self.urls: list[str] = []

    def download(
        self,
        url: str,
        destination: Path,
        expected_sha256: str,
        expected_size: int,
        progress=None,
    ) -> Path:
        self.urls.append(url)
        if self.failure:
            raise self.failure
        content = self.payloads[destination.relative_to(
            next(parent for parent in destination.parents if parent.name.startswith("staging-"))
        ).as_posix()]
        self.assert_record(content, expected_sha256, expected_size)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        if progress:
            progress(len(content))
        return destination

    @staticmethod
    def assert_record(content: bytes, expected_sha256: str, expected_size: int) -> None:
        if digest(content) != expected_sha256 or len(content) != expected_size:
            raise AssertionError("Test payload does not match manifest.")


class InstallerTests(unittest.TestCase):
    def test_install_reuses_files_downloads_changes_and_activates_atomically(self) -> None:
        old_payloads = {"Snake.exe": b"old exe", "assets/apple.png": b"same"}
        new_payloads = {
            "Snake.exe": b"new exe",
            "assets/apple.png": b"same",
            "assets/new file.txt": b"added",
        }
        old_manifest = Manifest.from_bytes(
            manifest_bytes(old_payloads, version="1.0.0")
        )
        new_manifest = Manifest.from_bytes(
            manifest_bytes(new_payloads, version="1.1.0")
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installer = Installer(
                root,
                "https://updates.example.test",
                downloader=RecordingDownloader(new_payloads),
            )
            installer.prepare()
            old_dir = root / "versions/1.0.0"
            for path, content in old_payloads.items():
                destination = old_dir / Path(path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            installer._write_installed_manifest(old_dir, old_manifest)
            old_release = ActiveRelease("1.0.0", "1.0.0", "Snake.exe")
            installer.activate(old_release)

            plan = UpdateChecker.plan(new_manifest, old_dir)
            new_release = installer.install(plan)
            previous = installer.activate(new_release)

            self.assertEqual(previous, old_release)
            self.assertEqual(installer.get_active(), new_release)
            self.assertEqual(
                (root / "versions/1.1.0/assets/apple.png").read_bytes(),
                b"same",
            )
            self.assertEqual(
                (root / "versions/1.1.0/assets/new file.txt").read_bytes(),
                b"added",
            )
            self.assertEqual(
                installer.downloader.urls,
                [
                    "https://updates.example.test/releases/1.1.0/Snake.exe",
                    "https://updates.example.test/releases/1.1.0/assets/new%20file.txt",
                ],
            )
            self.assertEqual(list((root / ".update").iterdir()), [])

    def test_rollback_restores_previous_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            installer = Installer(temporary, "https://updates.example.test")
            installer.prepare()
            previous = ActiveRelease("1.0.0", "1.0.0", "Snake.exe")
            current = ActiveRelease("1.1.0", "1.1.0", "Snake.exe")

            installer.activate(previous)
            returned_previous = installer.activate(current)
            installer.rollback(returned_previous)

            self.assertEqual(
                ActiveRelease.from_path(installer.active_path),
                previous,
            )
            self.assertEqual(
                list(Path(temporary).glob(".active.json.*.tmp")),
                [],
            )

    def test_failed_install_keeps_active_release_and_cleans_staging(self) -> None:
        payloads = {"Snake.exe": b"new exe"}
        manifest = Manifest.from_bytes(manifest_bytes(payloads))

        with tempfile.TemporaryDirectory() as temporary:
            installer = Installer(
                temporary,
                "https://updates.example.test",
                downloader=RecordingDownloader(
                    payloads,
                    failure=DownloadError("network unavailable"),
                ),
            )
            installer.prepare()
            previous = ActiveRelease("1.0.0", "1.0.0", "Snake.exe")
            installer.activate(previous)

            with self.assertRaises(InstallError):
                installer.install(UpdateChecker.plan(manifest, None))

            self.assertEqual(
                ActiveRelease.from_path(installer.active_path),
                previous,
            )
            self.assertEqual(list(installer.work_dir.iterdir()), [])
            self.assertFalse((installer.versions_dir / "1.1.0").exists())

    def test_prepare_removes_abandoned_staging_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            abandoned = root / ".update/staging-1.1.0-crashed"
            abandoned.mkdir(parents=True)
            (abandoned / "partial.bin").write_bytes(b"partial")

            installer = Installer(root, "https://updates.example.test")
            installer.prepare()

            self.assertFalse(abandoned.exists())


if __name__ == "__main__":
    unittest.main()
