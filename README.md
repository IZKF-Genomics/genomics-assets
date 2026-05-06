# genomics-assets

`genomics-assets` is the IZKF genomics facility repository for preparing and storing shared genomics assets in fixed server locations.

It covers:

- reference genomes and aligner indices
- contamination databases for Kraken2, Bracken, and FastQ Screen
- 10x Genomics reference bundles
- custom 10x Genomics references built with `cellranger mkref`
- 10x Linux binaries
- genome blacklists
- bundled control assets such as ERCC spike-ins

## Purpose

Use this repository when we need to build or fetch facility-wide assets in a reproducible way.
The bundled [`pixi` tasks](./pixi.toml) run the canonical commands with the repository's maintained config files and write results to the expected shared destinations.

## Setup

```bash
cd /data
gh repo clone IZKF-Genomics/genomics-assets
cd genomics-assets
pixi install
```

## Pixi Commands

The main day-to-day interface is `pixi run`:

```bash
pixi run ref-genomes
pixi run contamination-db
pixi run tenx
pixi run tenx-custom
pixi run tenx-binaries
pixi run blacklists
```

If needed, you can also call the CLI directly through Pixi:

```bash
pixi run python -m genomics_assets.cli ref-genomes build --config configs/ref_genomes.yaml --outdir /data/ref_genomes
pixi run python -m genomics_assets.cli tenx build-ref --config configs/ref_10xgenomics_custom.yaml --outdir /data/shared/10xGenomics/refs
```

## Command Map

Each bundled task uses a maintained config file and writes to a fixed destination:

| `pixi run` task | Config file | Result destination |
| --- | --- | --- |
| `ref-genomes` | [`configs/ref_genomes.yaml`](/data/genomics-assets/configs/ref_genomes.yaml) | `/data/ref_genomes` |
| `contamination-db` | [`configs/contamination_db.yaml`](/data/genomics-assets/configs/contamination_db.yaml) | `/data/shared/contamination_db` |
| `tenx` | [`configs/ref_10xgenomics.yaml`](/data/genomics-assets/configs/ref_10xgenomics.yaml) | `/data/shared/10xGenomics/refs` |
| `tenx-custom` | [`configs/ref_10xgenomics_custom.yaml`](/data/genomics-assets/configs/ref_10xgenomics_custom.yaml) | `/data/shared/10xGenomics/refs` |
| `tenx-binaries` | [`configs/tenx_binaries.yaml`](/data/genomics-assets/configs/tenx_binaries.yaml) | `/data/shared/10xGenomics/bin` |
| `blacklists` | [`configs/ref_genome_blacklists.yaml`](/data/genomics-assets/configs/ref_genome_blacklists.yaml) | `/data/ref_genome_blacklists` |

## Result Destinations

### Reference genomes

Built under:

```text
/data/ref_genomes/
  GRCh38/
    src/
      GRCh38.annotation.bed
      GRCh38.transcripts.fa
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

Run:

```bash
pixi run ref-genomes
```

The `ref-genomes` task also writes derived annotation assets used by `nf-core/rnaseq`:

- `<genome_id>.annotation.bed` from `gtf2bed`
- `<genome_id>.transcripts.fa` from `gffread`

To rebuild these derived files and any configured indices for all references:

```bash
cd /data/genomics-assets
pixi run ref-genomes
```

To force regeneration:

```bash
cd /data/genomics-assets
pixi run python -m genomics_assets.cli ref-genomes build \
  --config configs/ref_genomes.yaml \
  --outdir /data/ref_genomes \
  --force
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

Build metadata is also written under:

```text
configs/results/
  genome_manifest_resolved.csv
  db_build_info.yaml
```

Run:

```bash
pixi run contamination-db
```

### 10x references

Fetched under:

```text
/data/shared/10xGenomics/refs/
  refdata-gex-GRCh38-2024-A/
  refdata-gex-GRCm39-2024-A/
  refdata-gex-mRatBN7-2-2024-A/
  refdata-gex-GRCh38_and_GRCm39-2024-A/
  refdata-cellranger-vdj-GRCh38-alts-ensembl-7.1.0/
  refdata-cellranger-vdj-GRCm38-alts-ensembl-7.0.0/
  refdata-cellranger-arc-GRCh38-2024-A/
  refdata-cellranger-arc-GRCm39-2024-A/
```

Run:

```bash
pixi run tenx
```

### Custom 10x references

Built with `cellranger mkref` under the same shared destination, for example:

```text
/data/shared/10xGenomics/refs/
  refdata-gex-GRCz11-ensembl115-2026-A/
    fasta/
    genes/
    reference.json
    genomics_assets_build_info.yaml
  .build/
    refdata-gex-GRCz11-ensembl115-2026-A/
      Danio_rerio.GRCz11.115.filtered.gtf
```

The maintained recipe lives in:

- [`configs/ref_10xgenomics_custom.yaml`](/data/genomics-assets/configs/ref_10xgenomics_custom.yaml)

Run:

```bash
pixi run tenx-custom
```

Direct CLI form:

```bash
pixi run python -m genomics_assets.cli tenx build-ref \
  --config configs/ref_10xgenomics_custom.yaml \
  --outdir /data/shared/10xGenomics/refs
```

This task expects the stable Cell Ranger binary to be available at:

```text
/data/shared/10xGenomics/bin/cellranger
```

The build recipe records:

- source FASTA and GTF paths
- optional `mkgtf` filters
- Cell Ranger version
- threads, memory, and ref-version settings
- exact `mkgtf` and `mkref` commands used

Recommended facility pattern:

- reuse FASTA and GTF files already staged under `/data/ref_genomes/<genome>/src/`
- give each built reference a versioned `output_name`, for example `refdata-gex-GRCz11-ensembl115-2026-A`
- keep downloaded upstream 10x tarballs in [`configs/ref_10xgenomics.yaml`](/data/genomics-assets/configs/ref_10xgenomics.yaml)
- keep custom `mkref` recipes in [`configs/ref_10xgenomics_custom.yaml`](/data/genomics-assets/configs/ref_10xgenomics_custom.yaml)

For a new species or custom reference, the minimal inputs are:

- a matching FASTA
- a matching GTF
- an optional list of `cellranger mkgtf --attribute=...` filters
- enough memory and threads for `cellranger mkref`

### 10x Linux binaries

Downloaded under:

```text
/data/shared/10xGenomics/bin/
  cellranger-10.0.0/
  cellranger-atac-2.2.0/
  spaceranger-4.1.0/
  cellranger -> cellranger-10.0.0
  cellranger-atac -> cellranger-atac-2.2.0
  spaceranger -> spaceranger-4.1.0
```

Run:

```bash
pixi run tenx-binaries
```

To expose the stable binary symlinks on Linux shells, add this directory to `PATH`:

```bash
export PATH="/data/shared/10xGenomics/bin:$PATH"
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

Run:

```bash
pixi run blacklists
```

## Config Files

Quick links to the maintained configuration files:

- [`configs/ref_genomes.yaml`](/data/genomics-assets/configs/ref_genomes.yaml)
- [`configs/contamination_db.yaml`](/data/genomics-assets/configs/contamination_db.yaml)
- [`configs/ref_10xgenomics.yaml`](/data/genomics-assets/configs/ref_10xgenomics.yaml)
- [`configs/ref_10xgenomics_custom.yaml`](/data/genomics-assets/configs/ref_10xgenomics_custom.yaml)
- [`configs/tenx_binaries.yaml`](/data/genomics-assets/configs/tenx_binaries.yaml)
- [`configs/ref_genome_blacklists.yaml`](/data/genomics-assets/configs/ref_genome_blacklists.yaml)

## Repository Layout

- `configs/`: maintained config files
- `assets/`: bundled local assets such as ERCC references
- `src/genomics_assets/`: Python package and CLI
- `tests/`: smoke tests for config loading and artifact planning
- [`pixi.toml`](/data/genomics-assets/pixi.toml): task definitions used by `pixi run`
