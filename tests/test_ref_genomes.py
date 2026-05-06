from __future__ import annotations

from pathlib import Path

from genomics_assets import ref_genomes


def test_build_derived_assets_writes_expected_files(tmp_path: Path, monkeypatch) -> None:
    fasta = tmp_path / "genome.fa"
    gtf = tmp_path / "genes.gtf"
    fasta.write_text(">chr1\nACGT\n", encoding="utf-8")
    gtf.write_text(
        'chr1\tsrc\texon\t1\t4\t.\t+\t.\tgene_id "gene1"; transcript_id "tx1";\n',
        encoding="utf-8",
    )

    def fake_run(cmd, *, stdin=None, stdout=None, check=False):
        assert check is True
        if cmd == ["gtf2bed"]:
            stdout.write(b"chr1\t0\t4\tgene1\n")
            return None
        if cmd[:1] == ["gffread"]:
            Path(cmd[-1]).write_text(">tx1\nACGT\n", encoding="utf-8")
            return None
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(ref_genomes.subprocess, "run", fake_run)

    outputs = ref_genomes.build_derived_assets(
        "TestGenome",
        fasta,
        gtf,
        tmp_path,
        ["bed12", "transcript_fasta"],
        False,
    )

    assert outputs["bed12"] == tmp_path / "TestGenome.annotation.bed"
    assert outputs["transcript_fasta"] == tmp_path / "TestGenome.transcripts.fa"
    assert outputs["bed12"].read_text(encoding="utf-8") == "chr1\t0\t4\tgene1\n"
    assert outputs["transcript_fasta"].read_text(encoding="utf-8") == ">tx1\nACGT\n"


def test_salmon_and_kallisto_index_transcripts_when_available(tmp_path: Path, monkeypatch) -> None:
    fasta = tmp_path / "genome.fa"
    transcripts = tmp_path / "transcripts.fa"
    fasta.write_text(">chr1\nACGT\n", encoding="utf-8")
    transcripts.write_text(">tx1\nACGT\n", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run_cmd(cmd: list[str]) -> None:
        commands.append(cmd)

    monkeypatch.setattr(ref_genomes, "run_cmd", fake_run_cmd)

    ref_genomes.build_indices(
        "TestGenome",
        fasta,
        None,
        transcripts,
        tmp_path,
        ["salmon", "kallisto"],
        1,
        False,
    )

    assert ["salmon", "index", "-t", str(transcripts), "-i", str(tmp_path / "indices" / "salmon")] in commands
    assert [
        "kallisto",
        "index",
        "-i",
        str(tmp_path / "indices" / "kallisto" / "kallisto.idx"),
        str(transcripts),
    ] in commands
