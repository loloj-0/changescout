from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from changescout.models import DiscoveredUrlRecord, CrawlRecord


def load_discovered_url_records(path: Path) -> list[DiscoveredUrlRecord]:
    records: list[DiscoveredUrlRecord] = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL in {path} at line {line_number}: {exc.msg}"
                ) from exc

            if not isinstance(data, dict):
                raise ValueError(
                    f"Expected JSON object in {path} at line {line_number}"
                )

            try:
                record = DiscoveredUrlRecord(**data)
            except TypeError as exc:
                raise ValueError(
                    f"Invalid discovery record shape in {path} at line {line_number}: {exc}"
                ) from exc
            except ValueError as exc:
                raise ValueError(
                    f"Invalid discovery record in {path} at line {line_number}: {exc}"
                ) from exc

            records.append(record)

    return records


def write_crawl_records_jsonl(path: Path, records: list[CrawlRecord]) -> None:
    if not isinstance(path, Path):
        raise ValueError("path must be a Path")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            if not isinstance(record, CrawlRecord):
                raise ValueError("all records must be CrawlRecord instances")

            line = asdict(record)
            f.write(json.dumps(line, ensure_ascii=False) + "\n")