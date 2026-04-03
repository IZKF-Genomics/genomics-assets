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

## Layout

- `configs/`: starter configuration files
- `assets/`: bundled local assets such as ERCC references
- `src/genomics_assets/`: Python package and CLI
- `tests/`: smoke tests for config loading and artifact planning

## Notes

- The first version is a direct migration of the facility BPM templates into one standalone repo.
- `ref-genomes` and `contamination-db` are Python-backed builders.
- `tenx` and `blacklists` are lightweight download/fetch commands.

