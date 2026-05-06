from __future__ import annotations

import os
import subprocess
import sys


def test_cli_infer_help_is_available():
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "changescout.cli",
            "infer",
            "--help",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "cli.py infer" in result.stdout
    assert "--source-registry" in result.stdout
    assert "--canton-id" in result.stdout
    assert "--run-id" in result.stdout
    assert "--tfidf-model-artifact" in result.stdout
    assert "--enable-geoadmin-enrichment" in result.stdout
