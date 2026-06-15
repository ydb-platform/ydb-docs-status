#!/usr/bin/env python3
"""Fetch the YDB ``ydb/docs`` tree for a given version.

Usage::

    ./scripts/fetch.py <version> [--refresh]

The version name must exist in ``config.json``. A sparse, blob-filtered
shallow clone is used so only ``ydb/docs/`` is materialised on disk
(~tens of MB instead of ~2 GB). The clone lives at ``cache/<version>/``
with ``.git/`` at its root and the docs at ``cache/<version>/ydb/docs/``.

On subsequent runs the script reuses the existing clone and runs
``git fetch --depth=1 origin <ref> && git reset --hard FETCH_HEAD`` to
pick up any new commits on the branch (matters for ``main`` and for
``stable-*`` branches that get hotfixes). Pass ``--refresh`` to wipe
the clone and reclone from scratch instead.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import lib  # type: ignore[import-not-found]


def fetch(version: str, *, refresh: bool = False) -> Path:
    """Materialise ``cache/<version>/ydb/docs/`` from the remote repo.

    Returns the path to the populated ``ydb/docs/`` directory.
    """
    config = lib.load_config()
    entry = lib.require_version(version, config)
    ref = entry["ref"]
    repo = config["repo"]
    sparse_paths = config["sparse_paths"]

    cache_dir = lib.cache_version_dir(version)
    docs_dir = lib.docs_root(version)
    git_dir = cache_dir / ".git"

    if refresh and cache_dir.exists():
        print(f"[fetch] {version}: --refresh, removing existing {cache_dir}")
        shutil.rmtree(cache_dir)

    if git_dir.is_dir() and _remote_matches(cache_dir, repo):
        try:
            _update(version, cache_dir, ref, sparse_paths)
        except subprocess.CalledProcessError as exc:
            print(f"[fetch] {version}: update failed ({exc}), re-cloning")
            shutil.rmtree(cache_dir)

    if not git_dir.is_dir():
        if cache_dir.exists():
            print(f"[fetch] {version}: no usable clone in {cache_dir}, re-cloning")
            shutil.rmtree(cache_dir)
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        _clone(version, repo, ref, sparse_paths, cache_dir)

    if not docs_dir.is_dir():
        raise SystemExit(f"[fetch] {version}: expected {docs_dir} after sparse checkout, not found")

    print(f"[fetch] {version}: docs ready at {docs_dir}")
    return docs_dir


def _remote_matches(cache_dir: Path, expected_repo: str) -> bool:
    """Return True if ``origin`` in ``cache_dir`` points at ``expected_repo``."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cache_dir), "remote", "get-url", "origin"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError:
        return False
    return result.stdout.strip() == expected_repo


def _clone(version: str, repo: str, ref: str, sparse_paths: list[str], dest: Path) -> None:
    print(f"[fetch] {version}: cloning {repo} @ {ref} (sparse: {sparse_paths})")
    subprocess.run(
        [
            "git", "clone",
            "--depth", "1",
            "--branch", ref,
            "--filter=blob:none",
            "--sparse",
            repo,
            str(dest),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(dest), "sparse-checkout", "set", *sparse_paths],
        check=True,
    )


def _update(version: str, cache_dir: Path, ref: str, sparse_paths: list[str]) -> None:
    before = _head_sha(cache_dir)
    print(f"[fetch] {version}: fetching {ref} into existing clone at {cache_dir}")
    subprocess.run(
        ["git", "-C", str(cache_dir), "fetch", "--depth=1", "origin", ref],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(cache_dir), "reset", "--hard", "FETCH_HEAD"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(cache_dir), "sparse-checkout", "set", *sparse_paths],
        check=True,
    )
    after = _head_sha(cache_dir)
    if before == after:
        print(f"[fetch] {version}: already up-to-date at {after[:12]}")
    else:
        print(f"[fetch] {version}: updated {before[:12]} → {after[:12]}")


def _head_sha(cache_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(cache_dir), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="version key from config.json (e.g. 25.3)")
    parser.add_argument("--refresh", action="store_true", help="wipe and reclone instead of incremental fetch")
    args = parser.parse_args(argv)
    fetch(args.version, refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
