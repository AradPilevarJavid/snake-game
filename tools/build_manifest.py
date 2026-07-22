"""Generate a deterministic update manifest from a complete game payload."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


VERSION_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hash a PyInstaller onedir payload and write version.json."
    )
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", default="stable")
    parser.add_argument(
        "--update-mode", choices=("optional", "mandatory"), default="optional"
    )
    parser.add_argument("--minimum-supported-version")
    parser.add_argument("--release-notes", default="")
    parser.add_argument("--release-notes-file", type=Path)
    parser.add_argument("--entrypoint", default="Snake.exe")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        while chunk := file_handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_version(value: str) -> str:
    if not VERSION_RE.fullmatch(value):
        raise ValueError(f"Invalid semantic version: {value!r}")
    return value.removeprefix("v").split("+", 1)[0]


def build_manifest(args: argparse.Namespace) -> dict[str, object]:
    payload = args.payload.resolve()
    if not payload.is_dir():
        raise ValueError(f"Payload directory does not exist: {payload}")
    version = validate_version(args.version)
    minimum = (
        validate_version(args.minimum_supported_version)
        if args.minimum_supported_version
        else None
    )
    entrypoint = args.entrypoint.replace("\\", "/")
    entrypoint_path = payload.joinpath(*entrypoint.split("/"))
    if not entrypoint_path.is_file():
        raise ValueError(f"Entrypoint is missing from payload: {entrypoint}")

    release_notes = args.release_notes
    if args.release_notes_file:
        release_notes = args.release_notes_file.read_text(encoding="utf-8").strip()

    files: dict[str, dict[str, object]] = {}
    for path in sorted(
        (candidate for candidate in payload.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(payload).as_posix().casefold(),
    ):
        relative = path.relative_to(payload).as_posix()
        if relative == ".installed-manifest.json":
            continue
        files[relative] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }

    return {
        "schema_version": 1,
        "version": version,
        "channel": args.channel,
        "update_mode": args.update_mode,
        "minimum_supported_version": minimum,
        "release_notes": release_notes,
        "entrypoint": entrypoint,
        "files": files,
    }


def main() -> int:
    args = parse_args()
    try:
        manifest = build_manifest(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        f"Wrote {args.output} for {manifest['version']} "
        f"with {len(manifest['files'])} files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
