from __future__ import annotations

import argparse
from pathlib import Path

from .common import download_file, extract_tarball, load_yaml, log


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("tenx", help="Download and extract 10x Genomics reference bundles.")
    nested = parser.add_subparsers(dest="tenx_command", required=True)
    fetch = nested.add_parser("fetch", help="Fetch tarballs defined in a YAML config.")
    fetch.add_argument("--config", required=True)
    fetch.add_argument("--outdir", required=True)
    fetch.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    cfg = load_yaml(Path(args.config).resolve())
    urls = cfg.get("urls") or []
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    for url in urls:
        if not isinstance(url, str) or not url.strip():
            continue
        tarball = outdir / Path(url).name
        extracted_dir = outdir / tarball.name.removesuffix(".tar.gz")
        if extracted_dir.exists():
            log(f"skip extracted exists: {extracted_dir}")
            continue
        download_file(url, tarball)
        extract_tarball(tarball, outdir, delete_archive=True)
    return 0

