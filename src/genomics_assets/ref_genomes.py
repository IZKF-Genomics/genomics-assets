from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from .common import decompress_if_needed, download_file, ensure_dir, is_url, load_yaml, log, normalize_download_dest


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("ref-genomes", help="Download genomes and build aligner indices.")
    nested = parser.add_subparsers(dest="ref_genomes_command", required=True)
    build = nested.add_parser("build", help="Build reference genomes from a YAML config.")
    build.add_argument("--config", required=True)
    build.add_argument("--outdir", required=True)
    build.add_argument("--force", action="store_true")
    build.set_defaults(func=run)


def concat_files(parts: list[Path], dest: Path, force: bool) -> Path:
    ensure_dir(dest.parent)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        log(f"exists: {dest}")
        return dest
    with dest.open("wb") as f_out:
        for path in parts:
            with path.open("rb") as f_in:
                shutil.copyfileobj(f_in, f_out)
    return dest


def run_cmd(cmd: list[str]) -> None:
    log(" ".join(cmd))
    subprocess.run(cmd, check=True)


def tool_done(path: Path) -> Path:
    return path / ".done"


def should_skip(outdir: Path, force: bool) -> bool:
    return tool_done(outdir).exists() and not force


def mark_done(outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    tool_done(outdir).write_text("ok\n", encoding="utf-8")


def index_star(fasta: Path, gtf: Path | None, outdir: Path, threads: int) -> None:
    cmd = [
        "STAR", "--runMode", "genomeGenerate",
        "--runThreadN", str(threads),
        "--genomeDir", str(outdir),
        "--genomeFastaFiles", str(fasta),
    ]
    if gtf:
        cmd += ["--sjdbGTFfile", str(gtf)]
    run_cmd(cmd)


def index_bowtie2(fasta: Path, outdir: Path, prefix: str) -> None:
    run_cmd(["bowtie2-build", str(fasta), str(outdir / prefix)])


def index_bwa(fasta: Path, outdir: Path, prefix: str) -> None:
    run_cmd(["bwa", "index", "-p", str(outdir / prefix), str(fasta)])


def index_hisat2(fasta: Path, outdir: Path, prefix: str) -> None:
    run_cmd(["hisat2-build", str(fasta), str(outdir / prefix)])


def index_salmon(fasta: Path, outdir: Path) -> None:
    run_cmd(["salmon", "index", "-t", str(fasta), "-i", str(outdir)])


def index_kallisto(fasta: Path, outdir: Path) -> None:
    run_cmd(["kallisto", "index", "-i", str(outdir / "kallisto.idx"), str(fasta)])


def build_indices(genome_id: str, fasta: Path, gtf: Path | None, out_root: Path, tools: list[str], threads: int, force: bool) -> None:
    for tool in tools:
        tool_dir = out_root / "indices" / tool
        if should_skip(tool_dir, force):
            log(f"skip {genome_id} {tool} (exists)")
            continue
        ensure_dir(tool_dir)
        if tool == "star":
            index_star(fasta, gtf, tool_dir, threads)
        elif tool == "bowtie2":
            index_bowtie2(fasta, tool_dir, genome_id)
        elif tool == "bwa":
            index_bwa(fasta, tool_dir, genome_id)
        elif tool == "hisat2":
            index_hisat2(fasta, tool_dir, genome_id)
        elif tool == "salmon":
            index_salmon(fasta, tool_dir)
        elif tool == "kallisto":
            index_kallisto(fasta, tool_dir)
        else:
            raise SystemExit(f"Unknown tool: {tool}")
        mark_done(tool_dir)


def stage_source(src: str, dest_dir: Path, force: bool) -> Path:
    ensure_dir(dest_dir)
    dest = normalize_download_dest(dest_dir, src)
    if is_url(src):
        if force and dest.exists():
            dest.unlink()
        return download_file(src, dest)
    path = Path(src).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Source file does not exist: {src}")
    target = dest_dir / path.name
    if target.exists() and not force:
        log(f"exists: {target}")
        return target
    log(f"stage: {path} -> {target}")
    shutil.copyfile(path, target)
    return target


def run(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    outdir = Path(args.outdir).resolve()
    ensure_dir(outdir)
    cfg = load_yaml(config_path)
    defaults = cfg.get("defaults") or {}
    tools_default = list(defaults.get("tools") or [])
    threads = int(defaults.get("threads") or 16)
    with_ercc = bool(cfg.get("with_ercc", True))
    ercc_cfg = cfg.get("ercc") or {}
    ercc_fa = (config_path.parent / str(ercc_cfg.get("fasta", "../assets/ERCC92/ERCC92.fa"))).resolve()
    ercc_gtf = (config_path.parent / str(ercc_cfg.get("gtf", "../assets/ERCC92/ERCC92.gtf"))).resolve()

    log(f"Output root: {outdir}")
    log(f"Tools: {tools_default}")
    log(f"Threads: {threads}")

    for genome in cfg.get("genomes") or []:
        genome_id = genome.get("id")
        fasta_src = genome.get("fasta")
        if not genome_id or not fasta_src:
            continue
        gtf_src = genome.get("gtf")
        tools = list(genome.get("tools") or tools_default)

        genome_root = outdir / genome_id
        src_dir = genome_root / "src"
        fasta_staged = stage_source(str(fasta_src), src_dir, args.force)
        fasta_plain = decompress_if_needed(
            fasta_staged,
            src_dir / (fasta_staged.stem if fasta_staged.suffix == ".gz" else fasta_staged.name),
        )

        gtf_plain = None
        if gtf_src:
            gtf_staged = stage_source(str(gtf_src), src_dir, args.force)
            gtf_plain = decompress_if_needed(
                gtf_staged,
                src_dir / (gtf_staged.stem if gtf_staged.suffix == ".gz" else gtf_staged.name),
            )

        build_indices(str(genome_id), fasta_plain, gtf_plain, genome_root, tools, threads, args.force)

        if with_ercc:
            ercc_root = outdir / f"{genome_id}_with_ERCC"
            ercc_src = ercc_root / "src"
            ensure_dir(ercc_src)
            ercc_fa_out = ercc_src / f"{genome_id}_with_ERCC.fa"
            concat_files([fasta_plain, ercc_fa], ercc_fa_out, args.force)
            ercc_gtf_out = None
            if gtf_plain and ercc_gtf.exists():
                ercc_gtf_out = ercc_src / f"{genome_id}_with_ERCC.gtf"
                concat_files([gtf_plain, ercc_gtf], ercc_gtf_out, args.force)
            build_indices(f"{genome_id}_with_ERCC", ercc_fa_out, ercc_gtf_out, ercc_root, tools, threads, args.force)
    return 0

