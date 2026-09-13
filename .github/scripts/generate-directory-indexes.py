"""Generate browsable index.html files below dists/ and pool/."""

from __future__ import annotations

import html
import os
from pathlib import Path
import sys
from urllib.parse import quote


STYLE = """body{font:16px/1.6 system-ui,sans-serif;max-width:64rem;margin:2rem auto;padding:0 1rem;color:#202124;background:white}table{border-collapse:collapse;width:100%}td,th{padding:.45rem .7rem;border-bottom:1px solid #ddd;text-align:left}th:last-child,td:last-child{text-align:right}a{color:#006a55;text-decoration:none}a:hover{text-decoration:underline}code{font-size:.95em}"""


def display_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KiB"
    return f"{size / (1024 * 1024):.1f} MiB"


def write_index(root: Path, directory: Path) -> None:
    relative = directory.relative_to(root)
    title = f"FlowStation APT / {relative.as_posix()}"
    rows = ['<tr><td><a href="../">../</a></td><td>Verzeichnis</td><td></td></tr>']
    entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
    for entry in entries:
        if entry.name == "index.html" or entry.name.startswith("."):
            continue
        label = entry.name + ("/" if entry.is_dir() else "")
        href = quote(entry.name) + ("/" if entry.is_dir() else "")
        kind = "Verzeichnis" if entry.is_dir() else "Datei"
        size = "" if entry.is_dir() else display_size(entry.stat().st_size)
        rows.append(
            f'<tr><td><a href="{href}"><code>{html.escape(label)}</code></a></td>'
            f"<td>{kind}</td><td>{size}</td></tr>"
        )
    document = f"""<!doctype html>
<html lang="de">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{STYLE}</style>
<p><a href="{('../' * len(relative.parts))}">APT-Repository</a></p>
<h1>{html.escape(title)}</h1>
<table><thead><tr><th>Name</th><th>Typ</th><th>Groesse</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</html>
"""
    (directory / "index.html").write_text(document, encoding="utf-8", newline="\n")


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    for tree_name in ("dists", "pool"):
        tree = root / tree_name
        if tree.is_dir():
            for directory, child_dirs, _ in os.walk(tree):
                child_dirs.sort()
                write_index(root, Path(directory))


if __name__ == "__main__":
    main()
