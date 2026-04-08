from __future__ import annotations

import argparse
import tarfile
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

from genomics_assets.tenx import run_fetch_binaries


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def test_fetch_binaries_download_extract_and_link() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        serve_dir = root / "serve"
        outdir = root / "out"
        config_path = root / "tenx_binaries.yaml"

        tarballs = []
        for dirname, binary_name in [
            ("cellranger-10.0.0", "cellranger"),
            ("cellranger-atac-2.2.0", "cellranger-atac"),
            ("spaceranger-4.1.0", "spaceranger"),
        ]:
            payload_dir = serve_dir / dirname
            payload_dir.mkdir(parents=True, exist_ok=True)
            (payload_dir / binary_name).write_text("#!/bin/sh\n", encoding="utf-8")
            tarball = serve_dir / f"{dirname}.tar.gz"
            with tarfile.open(tarball, "w:gz") as handle:
                handle.add(payload_dir, arcname=payload_dir.name)
            tarballs.append(tarball)

        previous_cwd = Path.cwd()
        try:
            import os

            os.chdir(serve_dir)
            server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                config_path.write_text(
                    yaml.safe_dump(
                        {
                            "binaries": [
                                {
                                    "url": f"http://127.0.0.1:{server.server_port}/{tarballs[0].name}",
                                    "symlink_name": "cellranger",
                                },
                                {
                                    "url": f"http://127.0.0.1:{server.server_port}/{tarballs[1].name}",
                                    "symlink_name": "cellranger-atac",
                                },
                                {
                                    "url": f"http://127.0.0.1:{server.server_port}/{tarballs[2].name}",
                                    "symlink_name": "spaceranger",
                                },
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                args = argparse.Namespace(
                    config=str(config_path),
                    outdir=str(outdir),
                )
                assert run_fetch_binaries(args) == 0
            finally:
                server.shutdown()
                thread.join(timeout=5)
        finally:
            os.chdir(previous_cwd)

        for dirname, binary_name in [
            ("cellranger-10.0.0", "cellranger"),
            ("cellranger-atac-2.2.0", "cellranger-atac"),
            ("spaceranger-4.1.0", "spaceranger"),
        ]:
            extracted = outdir / dirname
            link_path = outdir / binary_name
            assert extracted.exists()
            assert (extracted / binary_name).exists()
            assert link_path.is_symlink()
            assert link_path.resolve() == extracted.resolve()
