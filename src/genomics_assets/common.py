from __future__ import annotations

import gzip
import hashlib
import shutil
import tarfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import yaml


def log(message: str) -> None:
    print(f"[genomics-assets] {message}")


def load_yaml(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise SystemExit(f"YAML file must contain a mapping: {path}")
    return raw


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, dest: Path) -> Path:
    ensure_dir(dest.parent)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"using cached download: {dest}")
        return dest
    log(f"download: {url} -> {dest}")
    request = urllib.request.Request(url, headers={"User-Agent": "genomics-assets/0.1.0"})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as out:
        shutil.copyfileobj(response, out)
    tmp.replace(dest)
    return dest


def normalize_download_dest(base: Path, src: str) -> Path:
    if is_url(src):
        return base / Path(urlparse(src).path).name
    return Path(src).expanduser().resolve()


def decompress_if_needed(src: Path, dest: Path) -> Path:
    ensure_dir(dest.parent)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"exists: {dest}")
        return dest
    if src.suffix == ".gz":
        log(f"decompress: {src.name} -> {dest.name}")
        with gzip.open(src, "rb") as f_in, dest.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        return dest
    shutil.copyfile(src, dest)
    return dest


def extract_tarball(tarball: Path, outdir: Path, *, delete_archive: bool = True) -> None:
    ensure_dir(outdir)
    log(f"extract: {tarball}")
    with tarfile.open(tarball, "r:gz") as handle:
        handle.extractall(outdir)
    if delete_archive:
        tarball.unlink(missing_ok=True)

