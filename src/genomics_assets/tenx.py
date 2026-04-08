from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

from .common import download_file, extract_tarball, load_yaml, log


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("tenx", help="Download and extract 10x Genomics reference bundles.")
    nested = parser.add_subparsers(dest="tenx_command", required=True)
    fetch = nested.add_parser("fetch", help="Fetch tarballs defined in a YAML config.")
    fetch.add_argument("--config", required=True)
    fetch.add_argument("--outdir", required=True)
    fetch.set_defaults(func=run_fetch)

    fetch_binaries = nested.add_parser(
        "fetch-binaries",
        help="Download and extract 10x Linux binary tarballs from a YAML config.",
    )
    fetch_binaries.add_argument("--config", required=True)
    fetch_binaries.add_argument("--outdir", required=True)
    fetch_binaries.set_defaults(func=run_fetch_binaries)


def run_fetch(args: argparse.Namespace) -> int:
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


def _safe_symlink(target: Path, link_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        if link_path.is_dir() and not link_path.is_symlink():
            raise SystemExit(f"Refusing to replace existing directory with symlink: {link_path}")
        link_path.unlink()
    relative_target = Path(os.path.relpath(target, start=link_path.parent))
    link_path.symlink_to(relative_target, target_is_directory=True)


def fetch_binary_entry(*, url: str, outdir: Path, symlink_name: str = "") -> Path:
    url = url.strip()
    if not url:
        raise SystemExit("binary download url must not be empty")
    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(url)
    tarball_name = Path(parsed.path).name
    if not tarball_name:
        raise SystemExit(f"Could not derive tarball filename from URL: {url}")
    tarball = outdir / tarball_name
    extracted_dir = outdir / tarball.name.removesuffix(".tar.gz")
    symlink_name = symlink_name.strip()

    if extracted_dir.exists():
        log(f"skip extracted exists: {extracted_dir}")
    else:
        download_file(url, tarball)
        extract_tarball(tarball, outdir, delete_archive=True)

    if not extracted_dir.exists():
        raise SystemExit(f"Expected extracted directory not found after download: {extracted_dir}")

    if symlink_name:
        link_path = outdir / symlink_name
        _safe_symlink(extracted_dir, link_path)
        log(f"symlink: {link_path} -> {extracted_dir.name}")
    return extracted_dir


def run_fetch_binaries(args: argparse.Namespace) -> int:
    cfg = load_yaml(Path(args.config).resolve())
    entries = cfg.get("binaries") or []
    if not isinstance(entries, list):
        raise SystemExit("binaries config must contain a list under 'binaries'")

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        if not isinstance(entry, dict):
            raise SystemExit("Each binaries entry must be a mapping")
        url = str(entry.get("url") or "").strip()
        symlink_name = str(entry.get("symlink_name") or "").strip()
        fetch_binary_entry(url=url, outdir=outdir, symlink_name=symlink_name)
    return 0
