#!/usr/bin/env python3
"""Fetch the YDB ``ydb/docs`` tree for a given version.

Usage::

    ./scripts/fetch.py <version> [--refresh]

The version name must exist in ``config.json``. A sparse, blob-filtered
shallow clone is used so only ``ydb/docs/`` is materialised on disk
(~tens of MB instead of ~2 GB). The result lands at
``cache/<version>/docs/``.

If the target directory already exists, the script is a no-op unless
``--refresh`` is passed, in which case the directory is replaced.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import lib  # type: ignore[import-not-found]


def fetch(version: str, *, refresh: bool = False) -> Path:
    """Materialise ``cache/<version>/docs/`` from the remote repo.

    Returns the path to the populated ``docs/`` directory.
    """
    config = lib.load_config()
    entry = lib.require_version(version, config)
    ref = entry["ref"]
    repo = config["repo"]
    sparse_paths = config["sparse_paths"]

    target = lib.docs_root(version)
    if target.exists():
        if not refresh:
            print(f"[fetch] {version}: {target} exists, skipping (use --refresh to redo)")
            return target
        print(f"[fetch] {version}: removing existing {target}")
        shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"ydb-fetch-{version}-") as tmp:
        tmp_path = Path(tmp) / "clone"
        print(f"[fetch] {version}: cloning {repo} @ {ref} (sparse: {sparse_paths})")
        subprocess.run(
            [
                "git", "clone",
                "--depth", "1",
                "--branch", ref,
                "--filter=blob:none",
                "--sparse",
                repo,
                str(tmp_path),
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "sparse-checkout", "set", *sparse_paths],
            check=True,
        )
        src = tmp_path / "ydb" / "docs"
        if not src.is_dir():
            raise SystemExit(f"[fetch] {version}: expected {src} after sparse checkout, not found")
        shutil.move(str(src), str(target))

    print(f"[fetch] {version}: docs ready at {target}")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="version key from config.json (e.g. 25.3)")
    parser.add_argument("--refresh", action="store_true", help="re-fetch even if local copy exists")
    args = parser.parse_args(argv)
    fetch(args.version, refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
