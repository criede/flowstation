"""Resolve a release to an immutable commit and a Debian version."""
import datetime as dt
import os
import re
import subprocess
import tomllib


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    tag = os.environ.get("RELEASE_TAG", "")
    source = os.environ.get("SOURCE_SHA", "")
    if source and not re.fullmatch(r"[0-9a-f]{40}", source):
        raise SystemExit("source_sha must be a full lowercase 40-character commit SHA")
    if tag and not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-db9cr\.[1-9][0-9]*)?", tag):
        raise SystemExit("Use vX.Y.Z or vX.Y.Z-db9cr.N")
    sha = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}" if tag else f"{source or 'HEAD'}^{{commit}}")
    if source and sha != source:
        raise SystemExit("Tag and source_sha identify different commits")
    base = tomllib.loads(git("show", f"{sha}:Cargo.toml"))["workspace"]["package"]["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", base):
        raise SystemExit("Expected a numeric X.Y.Z workspace version")
    if tag:
        if tag.removeprefix("v").split("-db9cr.")[0] != base:
            raise SystemExit("Tag version must match Cargo.toml workspace version")
        revision = tag.split("-db9cr.")[1] if "-db9cr." in tag else "1"
        version = f"{base}-{revision}"
        prerelease = "false"
    else:
        # Fixed-width UTC time and zero-padded run keep names sorted in build order.
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M")
        run = os.environ["GITHUB_RUN_NUMBER"].zfill(6)
        attempt = os.environ["GITHUB_RUN_ATTEMPT"]
        version = f"{base}+daily{stamp}.{run}.{attempt}.g{sha[:12]}-1"
        tag = f"daily-{version}"
        prerelease = "true"
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"sha={sha}\nversion={version}\ntag={tag}\nprerelease={prerelease}\n")


if __name__ == "__main__":
    main()
