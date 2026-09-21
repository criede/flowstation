"""Grandfather/father/son retention, limited to this fork's daily builds."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys

DAILY = re.compile(r"\+daily(\d{8})(?:\d{4})?\.(\d+)\.(\d+)\.g[0-9a-f]{12}-1(?:~(?:bookworm|trixie))?$")


def expired(entries, today=None):
    """Return expired IDs from (id, version) pairs; never prune stable versions."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    candidates = []
    for identifier, version in entries:
        match = DAILY.search(version)
        if match:
            day = dt.datetime.strptime(match[1], "%Y%m%d").date()
            candidates.append((day, int(match[2]), int(match[3]), identifier))
    seen = set()
    remove = []
    for day, run, attempt, identifier in sorted(candidates, reverse=True):
        age = (today - day).days
        if age < 7:
            continue
        bucket = ("week", *day.isocalendar()[:2]) if age < 30 else ("month", day.year, day.month)
        if age >= 365 or bucket in seen:
            remove.append(identifier)
        seen.add(bucket)
    # Always retain the newest daily, even if upstream has been quiet for a year.
    if candidates:
        newest = max(candidates)[3]
        remove = [item for item in remove if item != newest]
    return remove


def prune_pool(root):
    groups = {}
    for path in Path(root).glob("pool/*/main/f/flowstation/*.deb"):
        version = subprocess.check_output(["dpkg-deb", "-f", str(path), "Version"], text=True).strip()
        arch = subprocess.check_output(["dpkg-deb", "-f", str(path), "Architecture"], text=True).strip()
        groups.setdefault((path.parts[-5], arch), []).append((str(path), version))
    for entries in groups.values():
        for path in expired(entries):
            print(f"Pruning daily package {path}")
            Path(path).unlink()


def prune_releases():
    repo = os.environ["GH_REPO"]
    pages = json.loads(subprocess.check_output(
        ["gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100"], text=True))
    entries = [(item["tag_name"], item["tag_name"]) for page in pages for item in page
               if item["prerelease"] and not item["draft"] and item["tag_name"].startswith("daily-")]
    for tag in expired(entries):
        subprocess.run(["gh", "release", "delete", tag, "--yes", "--cleanup-tag"], check=True)


if __name__ == "__main__":
    if sys.argv[1] == "pool":
        prune_pool(sys.argv[2])
    elif sys.argv[1] == "releases":
        prune_releases()
    else:
        raise SystemExit("Expected pool <directory> or releases")
