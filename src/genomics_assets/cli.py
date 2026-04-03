from __future__ import annotations

import argparse

from . import __version__
from . import blacklists, contamination_db, ref_genomes, tenx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="genomics-assets", description="Manage shared facility genomics assets.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ref_genomes.add_parser(subparsers)
    contamination_db.add_parser(subparsers)
    tenx.add_parser(subparsers)
    blacklists.add_parser(subparsers)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

