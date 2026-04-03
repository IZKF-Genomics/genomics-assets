from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_configs_exist_and_load() -> None:
    for name in [
        "ref_genomes.yaml",
        "contamination_db.yaml",
        "ref_10xgenomics.yaml",
        "ref_genome_blacklists.yaml",
    ]:
        path = ROOT / "configs" / name
        assert path.exists()
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)


def test_ercc_assets_exist() -> None:
    assert (ROOT / "assets" / "ERCC92" / "ERCC92.fa").exists()
    assert (ROOT / "assets" / "ERCC92" / "ERCC92.gtf").exists()

