from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json

from changescout.config import ScopeConfig, SourceConfig


def build_snapshot_payload(
    scope: ScopeConfig,
    active_sources: list[SourceConfig],
) -> dict[str, Any]:
    return {
        "snapshot_created_at": datetime.now(timezone.utc).isoformat(),
        "scope": asdict(scope),
        "active_sources": [asdict(source) for source in active_sources],
    }


def write_snapshot(
    output_dir: str | Path,
    scope: ScopeConfig,
    active_sources: list[SourceConfig],
    filename: str = "resolved_scope_snapshot.json",
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = output_dir / filename
    payload = build_snapshot_payload(scope, active_sources)

    snapshot_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return snapshot_path