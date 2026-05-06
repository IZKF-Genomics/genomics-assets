from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .common import download_file, ensure_dir, extract_tarball, load_yaml, log


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

    build_ref = nested.add_parser(
        "build-ref",
        help="Build custom Cell Ranger reference bundles from a YAML config.",
    )
    build_ref.add_argument("--config", required=True)
    build_ref.add_argument("--outdir", required=True)
    build_ref.add_argument("--force", action="store_true")
    build_ref.set_defaults(func=run_build_ref)


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


def require(value: Any, message: str) -> Any:
    if value in (None, "", []):
        raise SystemExit(message)
    return value


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def resolve_cellranger_binary(binary: str) -> Path:
    candidate = binary.strip()
    if not candidate:
        raise SystemExit("cellranger_bin must not be empty")
    if any(sep in candidate for sep in ("/", os.sep)):
        path = Path(candidate).expanduser().resolve()
    else:
        found = shutil.which(candidate)
        if not found:
            raise SystemExit(f"cellranger binary not found on PATH: {candidate}")
        path = Path(found).resolve()
    if not path.exists():
        raise SystemExit(f"cellranger binary does not exist: {path}")
    if not path.is_file():
        raise SystemExit(f"cellranger binary is not a file: {path}")
    if not os.access(path, os.X_OK):
        raise SystemExit(f"cellranger binary is not executable: {path}")
    return path


def run_cmd(cmd: list[str], *, cwd: Path | None = None) -> None:
    log("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def command_output(cmd: list[str]) -> str:
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        return str(exc)
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    return output.splitlines()[0] if output else ""


def as_custom_reference_entries(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    entries = cfg.get("references") or []
    if not isinstance(entries, list):
        raise SystemExit("custom 10x ref config must contain a list under 'references'")
    selected = [entry for entry in entries if isinstance(entry, dict) and entry.get("enabled", True)]
    if not selected:
        raise SystemExit("No enabled custom 10x references configured.")
    return selected


def normalize_attributes(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise SystemExit("mkgtf_attributes must be a list of strings")
    attrs = [str(item).strip() for item in value if str(item).strip()]
    if not attrs:
        return []
    return attrs


def custom_build_info(
    *,
    ref_id: str,
    output_name: str,
    fasta: Path,
    gtf: Path,
    used_gtf: Path,
    filtered_gtf: Path | None,
    work_dir: Path,
    config_path: Path,
    cellranger_bin: Path,
    cellranger_version: str,
    ref_version: str,
    nthreads: int,
    memgb: int,
    mkgtf_attributes: list[str],
    mkgtf_command: list[str] | None,
    mkref_command: list[str],
) -> dict[str, Any]:
    return {
        "id": ref_id,
        "output_name": output_name,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "work_dir": str(work_dir),
        "cellranger_bin": str(cellranger_bin),
        "cellranger_version": cellranger_version,
        "ref_version": ref_version,
        "nthreads": nthreads,
        "memgb": memgb,
        "input_fasta": str(fasta),
        "input_gtf": str(gtf),
        "filtered_gtf": str(filtered_gtf) if filtered_gtf is not None else "",
        "used_gtf": str(used_gtf),
        "mkgtf_attributes": mkgtf_attributes,
        "commands": {
            "mkgtf": mkgtf_command or [],
            "mkref": mkref_command,
        },
    }


def run_build_ref(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    cfg = load_yaml(config_path)
    defaults = cfg.get("defaults") or {}
    entries = as_custom_reference_entries(cfg)
    outdir = Path(args.outdir).resolve()
    ensure_dir(outdir)
    build_root = outdir / ".build"
    ensure_dir(build_root)

    binary_value = str(defaults.get("cellranger_bin") or "/data/shared/10xGenomics/bin/cellranger")
    cellranger_bin = resolve_cellranger_binary(binary_value)
    cellranger_version = command_output([str(cellranger_bin), "--version"])
    default_threads = int(defaults.get("nthreads") or 16)
    default_memgb = int(defaults.get("memgb") or 64)
    default_ref_version = str(defaults.get("ref_version") or "")
    build_info_name = str(defaults.get("build_info_name") or "genomics_assets_build_info.yaml").strip()

    for entry in entries:
        ref_id = str(require(entry.get("id"), "Each enabled custom 10x reference needs an id.")).strip()
        output_name = str(entry.get("output_name") or ref_id).strip()
        if not output_name:
            raise SystemExit(f"Custom 10x reference '{ref_id}' needs a non-empty output_name.")
        fasta = Path(str(require(entry.get("fasta"), f"Custom 10x reference '{ref_id}' is missing fasta."))).expanduser().resolve()
        gtf = Path(str(require(entry.get("gtf"), f"Custom 10x reference '{ref_id}' is missing gtf."))).expanduser().resolve()
        if not fasta.exists():
            raise SystemExit(f"FASTA file does not exist for '{ref_id}': {fasta}")
        if not gtf.exists():
            raise SystemExit(f"GTF file does not exist for '{ref_id}': {gtf}")

        target_dir = outdir / output_name
        if target_dir.exists():
            if not args.force:
                log(f"skip extracted exists: {target_dir}")
                continue
            shutil.rmtree(target_dir)

        work_dir = build_root / output_name
        if work_dir.exists() and args.force:
            shutil.rmtree(work_dir)
        ensure_dir(work_dir)

        mkgtf_attributes = normalize_attributes(entry.get("mkgtf_attributes"))
        gtf_output_name = str(entry.get("filtered_gtf_name") or f"{gtf.stem}.filtered.gtf").strip()
        filtered_gtf = work_dir / gtf_output_name if mkgtf_attributes else None
        used_gtf = filtered_gtf or gtf
        mkgtf_command: list[str] | None = None
        if filtered_gtf is not None:
            mkgtf_command = [str(cellranger_bin), "mkgtf", str(gtf), str(filtered_gtf)]
            for attribute in mkgtf_attributes:
                mkgtf_command.append(f"--attribute={attribute}")
            run_cmd(mkgtf_command)

        nthreads = int(entry.get("nthreads") or default_threads)
        memgb = int(entry.get("memgb") or default_memgb)
        ref_version = str(entry.get("ref_version") or default_ref_version).strip()
        mkref_command = [
            str(cellranger_bin),
            "mkref",
            f"--genome={output_name}",
            f"--fasta={fasta}",
            f"--genes={used_gtf}",
            f"--nthreads={nthreads}",
            f"--memgb={memgb}",
        ]
        if ref_version:
            mkref_command.append(f"--ref-version={ref_version}")
        run_cmd(mkref_command, cwd=outdir)

        if not target_dir.exists():
            raise SystemExit(f"Expected built reference directory not found after mkref: {target_dir}")

        build_info = custom_build_info(
            ref_id=ref_id,
            output_name=output_name,
            fasta=fasta,
            gtf=gtf,
            used_gtf=used_gtf,
            filtered_gtf=filtered_gtf,
            work_dir=work_dir,
            config_path=config_path,
            cellranger_bin=cellranger_bin,
            cellranger_version=cellranger_version,
            ref_version=ref_version,
            nthreads=nthreads,
            memgb=memgb,
            mkgtf_attributes=mkgtf_attributes,
            mkgtf_command=mkgtf_command,
            mkref_command=mkref_command,
        )
        write_yaml(target_dir / build_info_name, build_info)
    return 0
