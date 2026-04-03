# genomics-assets

`genomics-assets` manages shared reference and QC assets for the IZKF genomics facility.

It groups facility infrastructure that was previously spread across several BPM templates:

- reference genomes and aligner indices
- contamination databases for Kraken2, Bracken, and FastQ Screen
- 10x Genomics reference bundles
- genome blacklists
- bundled control assets such as ERCC spike-ins

## Commands

```bash
genomics-assets ref-genomes build --config configs/ref_genomes.yaml --outdir /data/ref_genomes
genomics-assets contamination-db build --config configs/contamination_db.yaml
genomics-assets tenx fetch --config configs/ref_10xgenomics.yaml --outdir /data/shared/10xGenomics
genomics-assets blacklists fetch --config configs/ref_genome_blacklists.yaml --outdir /data/ref_genome_blacklists
```

## Quickstart

Recommended facility workflow:

```bash
cd /data
gh repo clone IZKF-Genomics/genomics-assets
cd genomics-assets
pixi install
```

Then run one of the bundled tasks:

```bash
pixi run ref-genomes
pixi run contamination-db
pixi run tenx
pixi run blacklists
```

You can also call the CLI directly through Pixi:

```bash
pixi run python -m genomics_assets.cli ref-genomes build --config configs/ref_genomes.yaml --outdir /data/ref_genomes
```

Currently configured Pixi tasks:

- `ref-genomes`
- `contamination-db`
- `tenx`
- `blacklists`
- `test`

## Fixed server paths

This repository intentionally uses fixed result paths because that is how assets are organized on the facility servers.
The starter configs are not generic examples. They reflect the current canonical server layout.

Default targets from the bundled configs:

- `ref-genomes`: `/data/ref_genomes`
- `contamination-db`: `/data/shared/contamination_db`
- `tenx`: `/data/shared/10xGenomics`
- `blacklists`: `/data/ref_genome_blacklists`

## Result layout

Quick overview of where assets end up after a build or fetch:

### Reference genomes

Built under:

```text
/data/ref_genomes/
  GRCh38/
    src/
    indices/
      star/
      bowtie2/
      bwa/
      hisat2/
      salmon/
      kallisto/
  GRCh38_with_ERCC/
    src/
    indices/
      star/
      bowtie2/
      bwa/
      hisat2/
      salmon/
      kallisto/
  GRCm39/
  GRCm39_with_ERCC/
  ...
```

### Contamination databases

Built under:

```text
/data/shared/contamination_db/
  kraken2/
    vertebrate_panel/
      v2026.03/
      current -> v2026.03
  bracken/
    vertebrate_panel/
      v2026.03/
        readlen_75/
        readlen_100/
        readlen_151/
      current -> v2026.03
  fastq_screen/
    vertebrate_panel/
      v2026.03/
        indexes/
        fastq_screen.conf
      current -> v2026.03
```

Build metadata is written next to the config under:

```text
configs/results/
  genome_manifest_resolved.csv
  db_build_info.yaml
```

### 10x references

Fetched under:

```text
/data/shared/10xGenomics/
  refdata-gex-GRCh38-2024-A/
  refdata-gex-GRCm39-2024-A/
  refdata-gex-mRatBN7-2-2024-A/
  refdata-gex-GRCh38_and_GRCm39-2024-A/
  refdata-cellranger-vdj-GRCh38-alts-ensembl-7.1.0/
  refdata-cellranger-vdj-GRCm38-alts-ensembl-7.0.0/
```

### Genome blacklists

Fetched under:

```text
/data/ref_genome_blacklists/
  ce10-blacklist.v2.bed.gz
  ce11-blacklist.v2.bed.gz
  dm3-blacklist.v2.bed.gz
  dm6-blacklist.v2.bed.gz
  hg19-blacklist.v2.bed.gz
  hg38-blacklist.v2.bed.gz
  mm10-blacklist.v2.bed.gz
```

## Layout

- `configs/`: starter configuration files
- `assets/`: bundled local assets such as ERCC references
- `src/genomics_assets/`: Python package and CLI
- `tests/`: smoke tests for config loading and artifact planning

## Notes

- The first version is a direct migration of the facility BPM templates into one standalone repo.
- `ref-genomes` and `contamination-db` are Python-backed builders.
- `tenx` and `blacklists` are lightweight download/fetch commands.
- If the facility server layout changes later, update the bundled configs and this README together so the documented paths stay authoritative.
