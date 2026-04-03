from __future__ import annotations

import argparse
from pathlib import Path

from .common import download_file, load_yaml


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("blacklists", help="Download genome blacklist BED files.")
    nested = parser.add_subparsers(dest="blacklists_command", required=True)
    fetch = nested.add_parser("fetch", help="Fetch blacklist files defined in a YAML config.")
    fetch.add_argument("--config", required=True)
    fetch.add_argument("--outdir", required=True)
    fetch.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    cfg = load_yaml(Path(args.config).resolve())
    base_url = str(cfg.get("base_url") or "").rstrip("/")
    files = cfg.get("files") or []
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    for name in files:
        if not isinstance(name, str) or not name.strip():
            continue
        download_file(f"{base_url}/{name}", outdir / name)
    return 0

