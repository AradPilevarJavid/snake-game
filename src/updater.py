import json
import re
import urllib.error
import urllib.request
import webbrowser

from config import VERSION

GITHUB_OWNER = "AradPilevarJavid"
GITHUB_REPO = "snake-game"
LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


def parse_version(version):
    match = re.search(r"(\d+(?:\.\d+)*)", version)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(latest_tag, current_version=VERSION):
    latest = parse_version(latest_tag)
    current = parse_version(current_version)
    if not latest or not current:
        return False
    max_len = max(len(latest), len(current))
    latest += (0,) * (max_len - len(latest))
    current += (0,) * (max_len - len(current))
    return latest > current


def check_for_updates(open_release=True, timeout=3):
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"SnakeGame/{VERSION}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            release = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None

    latest_tag = release.get("tag_name", "")
    release_url = release.get("html_url") or RELEASES_URL
    if not is_newer_version(latest_tag):
        return None

    if open_release:
        webbrowser.open(release_url)

    return {
        "current_version": VERSION,
        "latest_tag": latest_tag,
        "url": release_url,
    }
