from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse
import json

import yaml

from changescout.config import load_source_registry
from changescout.discovery import discover_urls_from_source, write_discovery_jsonl


SUPPORTED_CRAWL_TYPES = {"html_pattern"}
BROAD_INCLUDE_PATTERNS = {
    "/",
    "/de/",
    "/fr/",
    "/it/",
    "/en/",
    "/news/",
    "/aktuell/",
    "/detail/",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML object in {path}")

    return data


def is_valid_http_url(value: Any) -> bool:
    text = str(value or "").strip()

    try:
        parsed = urlparse(text)
    except ValueError:
        return False

    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def add_issue(
    issues: List[Dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    source_id: str = "",
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "source_id": source_id,
            "message": message,
        }
    )


def validate_registry_file(
    config_dir: Path,
    source_registry: str,
) -> Dict[str, Any]:
    registry_path = config_dir / "sources" / f"{source_registry}.yaml"

    issues: List[Dict[str, Any]] = []

    if not registry_path.exists():
        add_issue(
            issues,
            severity="error",
            code="registry_file_missing",
            message=f"Registry file does not exist: {registry_path}",
        )

        return {
            "registry": source_registry,
            "registry_path": str(registry_path),
            "valid": False,
            "checked_at": utc_now_iso(),
            "source_count": 0,
            "active_source_count": 0,
            "error_count": 1,
            "warning_count": 0,
            "issues": issues,
        }

    raw = read_yaml(registry_path)
    sources = raw.get("sources")

    if not isinstance(sources, list):
        add_issue(
            issues,
            severity="error",
            code="sources_not_list",
            message="Registry field 'sources' must be a list.",
        )
        sources = []

    if not sources:
        add_issue(
            issues,
            severity="error",
            code="empty_registry",
            message="Registry contains no sources.",
        )

    required_fields = [
        "source_id",
        "name",
        "base_url",
        "crawl_type",
        "crawl_frequency_hours",
        "active",
    ]

    seen_source_ids: set[str] = set()
    active_source_count = 0

    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            add_issue(
                issues,
                severity="error",
                code="source_not_object",
                message=f"Source at index {index} must be an object.",
            )
            continue

        source_id = str(source.get("source_id") or f"<index:{index}>")

        for field in required_fields:
            if field not in source:
                add_issue(
                    issues,
                    severity="error",
                    code="missing_required_field",
                    source_id=source_id,
                    message=f"Missing required field: {field}",
                )

        if source_id in seen_source_ids:
            add_issue(
                issues,
                severity="error",
                code="duplicate_source_id",
                source_id=source_id,
                message=f"Duplicate source_id: {source_id}",
            )
        else:
            seen_source_ids.add(source_id)

        if source.get("active") is True:
            active_source_count += 1

        crawl_type = str(source.get("crawl_type") or "")

        if crawl_type not in SUPPORTED_CRAWL_TYPES:
            add_issue(
                issues,
                severity="error",
                code="unsupported_crawl_type",
                source_id=source_id,
                message=f"Unsupported crawl_type: {crawl_type}",
            )

        base_url = source.get("base_url")

        if not is_valid_http_url(base_url):
            add_issue(
                issues,
                severity="error",
                code="invalid_base_url",
                source_id=source_id,
                message=f"Invalid base_url: {base_url}",
            )

        include_patterns = source.get("include_patterns")

        if crawl_type == "html_pattern":
            if not isinstance(include_patterns, list) or not include_patterns:
                add_issue(
                    issues,
                    severity="error",
                    code="missing_include_patterns",
                    source_id=source_id,
                    message="html_pattern sources require non empty include_patterns.",
                )
            else:
                for pattern in include_patterns:
                    pattern_text = str(pattern or "").strip()

                    if not pattern_text:
                        add_issue(
                            issues,
                            severity="error",
                            code="empty_include_pattern",
                            source_id=source_id,
                            message="include_patterns must not contain empty strings.",
                        )

                    if pattern_text in BROAD_INCLUDE_PATTERNS:
                        add_issue(
                            issues,
                            severity="warning",
                            code="broad_include_pattern",
                            source_id=source_id,
                            message=f"Include pattern may be too broad: {pattern_text}",
                        )

                    if len(pattern_text) < 4:
                        add_issue(
                            issues,
                            severity="warning",
                            code="short_include_pattern",
                            source_id=source_id,
                            message=f"Include pattern is very short: {pattern_text}",
                        )

    if active_source_count == 0:
        add_issue(
            issues,
            severity="error",
            code="no_active_sources",
            message="Registry contains no active sources.",
        )

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    return {
        "registry": source_registry,
        "registry_path": str(registry_path),
        "valid": error_count == 0,
        "checked_at": utc_now_iso(),
        "source_count": int(len(sources)),
        "active_source_count": int(active_source_count),
        "error_count": int(error_count),
        "warning_count": int(warning_count),
        "issues": issues,
    }


def run_discovery_smoke_test(
    config_dir: Path,
    source_registry: str,
    output_dir: Path,
    timeout_seconds: int = 10,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = load_source_registry(config_dir / "sources" / f"{source_registry}.yaml")

    records = []
    source_summaries = []

    for source in sources:
        if not source.active:
            source_summaries.append(
                {
                    "source_id": source.source_id,
                    "active": source.active,
                    "discovered_records": 0,
                    "status": "skipped_inactive",
                    "error": "",
                }
            )
            continue

        try:
            source_records = discover_urls_from_source(
                source=source,
                timeout=timeout_seconds,
            )
            records.extend(source_records)

            source_summaries.append(
                {
                    "source_id": source.source_id,
                    "active": source.active,
                    "discovered_records": int(len(source_records)),
                    "status": "success",
                    "error": "",
                }
            )

        except Exception as exc:
            source_summaries.append(
                {
                    "source_id": source.source_id,
                    "active": source.active,
                    "discovered_records": 0,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    discovery_output_path = output_dir / "discovery_smoke.jsonl"
    write_discovery_jsonl(records, discovery_output_path)

    failed_sources = [
        item for item in source_summaries if item["status"] == "failed"
    ]

    zero_active_sources = [
        item
        for item in source_summaries
        if item["active"] is True and item["status"] == "success" and item["discovered_records"] == 0
    ]

    report = {
        "registry": source_registry,
        "output_dir": str(output_dir),
        "discovery_output_path": str(discovery_output_path),
        "checked_at": utc_now_iso(),
        "total_records": int(len(records)),
        "source_summaries": source_summaries,
        "failed_source_count": int(len(failed_sources)),
        "zero_record_active_source_count": int(len(zero_active_sources)),
        "status": "success" if not failed_sources else "failed",
        "warnings": [
            f"Active source produced zero records: {item['source_id']}"
            for item in zero_active_sources
        ],
    }

    write_json(output_dir / "discovery_smoke_report.json", report)

    return report


def run_registry_validation(
    config_dir: Path,
    source_registry: str,
    output_dir: Path | None = None,
    smoke_discovery: bool = False,
    timeout_seconds: int = 10,
) -> Dict[str, Any]:
    validation_report = validate_registry_file(
        config_dir=config_dir,
        source_registry=source_registry,
    )

    smoke_report = None

    if smoke_discovery and validation_report["valid"]:
        if output_dir is None:
            output_dir = Path("artifacts") / "registry_validation" / source_registry

        smoke_report = run_discovery_smoke_test(
            config_dir=config_dir,
            source_registry=source_registry,
            output_dir=output_dir,
            timeout_seconds=timeout_seconds,
        )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "registry_validation_report.json", validation_report)

    return {
        "validation": validation_report,
        "smoke_discovery": smoke_report,
    }
