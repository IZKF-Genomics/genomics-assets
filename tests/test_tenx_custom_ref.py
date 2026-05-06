from __future__ import annotations

import argparse
import gzip
import tempfile
from pathlib import Path

import yaml

from genomics_assets.tenx import run_build_ref


def make_fake_cellranger(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import shutil
import sys
from pathlib import Path


def parse_option(args: list[str], prefix: str) -> str:
    for value in args:
        if value.startswith(prefix):
            return value.split("=", 1)[1]
    raise SystemExit(f"missing option: {prefix}")


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        raise SystemExit("missing subcommand")
    if argv == ["--version"]:
        print("cellranger 10.0.0")
        return 0
    cmd = argv[0]
    if cmd == "mkgtf":
        input_gtf = Path(argv[1])
        output_gtf = Path(argv[2])
        attrs = [item.split("=", 1)[1] for item in argv[3:] if item.startswith("--attribute=")]
        keep_tokens = [attr.split(":", 1)[1] for attr in attrs]
        output_gtf.parent.mkdir(parents=True, exist_ok=True)
        with input_gtf.open("r", encoding="utf-8") as src, output_gtf.open("w", encoding="utf-8") as dst:
            for line in src:
                if not keep_tokens or any(token in line for token in keep_tokens):
                    dst.write(line)
        return 0
    if cmd == "mkref":
        genome = parse_option(argv[1:], "--genome=")
        fasta = Path(parse_option(argv[1:], "--fasta="))
        genes = Path(parse_option(argv[1:], "--genes="))
        outdir = Path.cwd() / genome
        (outdir / "fasta").mkdir(parents=True, exist_ok=True)
        (outdir / "genes").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fasta, outdir / "fasta" / "genome.fa")
        (outdir / "fasta" / "genome.fa.fai").write_text("chr1\\t4\\t0\\t4\\t5\\n", encoding="utf-8")
        with genes.open("rb") as src, gzip.open(outdir / "genes" / "genes.gtf.gz", "wb") as dst:
            shutil.copyfileobj(src, dst)
        (outdir / "reference.json").write_text(json.dumps({"genome": genome}), encoding="utf-8")
        return 0
    raise SystemExit(f"unsupported fake cellranger subcommand: {cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_build_custom_cellranger_ref() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        outdir = root / "refs"
        fasta = root / "Danio_rerio.GRCz11.dna.toplevel.fa"
        gtf = root / "Danio_rerio.GRCz11.115.gtf"
        cellranger = root / "cellranger"
        config_path = root / "ref_10xgenomics_custom.yaml"

        fasta.write_text(">chr1\nACGT\n", encoding="utf-8")
        gtf.write_text(
            "\n".join(
                [
                    'chr1\tsrc\texon\t1\t4\t.\t+\t.\tgene_id "g_pc"; transcript_id "t_pc"; gene_name "pc"; gene_biotype "protein_coding";',
                    'chr1\tsrc\texon\t1\t4\t.\t+\t.\tgene_id "g_nc"; transcript_id "t_nc"; gene_name "nc"; gene_biotype "lncRNA";',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        make_fake_cellranger(cellranger)

        config_path.write_text(
            yaml.safe_dump(
                {
                    "defaults": {
                        "cellranger_bin": str(cellranger),
                        "nthreads": 8,
                        "memgb": 32,
                        "ref_version": "Ensembl-115",
                    },
                    "references": [
                        {
                            "id": "GRCz11",
                            "output_name": "refdata-gex-GRCz11-ensembl115-2026-A",
                            "fasta": str(fasta),
                            "gtf": str(gtf),
                            "mkgtf_attributes": ["gene_biotype:protein_coding"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        args = argparse.Namespace(
            config=str(config_path),
            outdir=str(outdir),
            force=False,
        )
        assert run_build_ref(args) == 0

        refdir = outdir / "refdata-gex-GRCz11-ensembl115-2026-A"
        assert refdir.exists()
        assert (refdir / "fasta" / "genome.fa").exists()
        assert (refdir / "genes" / "genes.gtf.gz").exists()
        assert (refdir / "reference.json").exists()

        build_info = yaml.safe_load((refdir / "genomics_assets_build_info.yaml").read_text(encoding="utf-8"))
        assert build_info["id"] == "GRCz11"
        assert build_info["output_name"] == "refdata-gex-GRCz11-ensembl115-2026-A"
        assert build_info["cellranger_version"] == "cellranger 10.0.0"
        assert build_info["nthreads"] == 8
        assert build_info["memgb"] == 32
        assert build_info["ref_version"] == "Ensembl-115"
        assert build_info["mkgtf_attributes"] == ["gene_biotype:protein_coding"]
        filtered_gtf = Path(build_info["filtered_gtf"])
        assert filtered_gtf.exists()
        filtered_text = filtered_gtf.read_text(encoding="utf-8")
        assert "protein_coding" in filtered_text
        assert "lncRNA" not in filtered_text
        assert build_info["commands"]["mkgtf"]
        assert build_info["commands"]["mkref"]
