import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Set


DEFAULT_KEYWORDS = [
    "strasse",
    "strassen",
    "kantonsstrasse",
    "verkehr",
    "gesamtverkehr",
    "mobilität",
    "mobilitaet",
    "mobilitätsdrehscheibe",
    "mobilitaetsdrehscheibe",
    "bahnhof",
    "brücke",
    "bruecke",
    "steg",
    "tunnel",
    "unterführung",
    "unterfuehrung",
    "kreisel",
    "knoten",
    "radweg",
    "velo",
    "fussweg",
    "gehweg",
    "haltestelle",
    "sanierung",
    "belag",
    "baustelle",
    "bauarbeiten",
    "sperrung",
    "vollsperrung",
    "umfahrung",
    "erschliessung",
    "stützmauer",
    "stuetzmauer",
]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError("Invalid JSON at line {}: {}".format(line_number, path)) from error

            if not isinstance(record, dict):
                raise ValueError("Expected JSON object at line {}: {}".format(line_number, path))

            records.append(record)

    return records


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_score(record: Dict[str, Any]) -> float:
    value = record.get("thematic_score", 0)

    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def build_keyword_pattern(keywords: List[str]) -> Pattern:
    escaped = [re.escape(keyword) for keyword in keywords]
    return re.compile("|".join(escaped), re.IGNORECASE)


def keyword_search_text(record: Dict[str, Any], context_chars: int) -> str:
    title = str(record.get("title") or "")
    clean_text = str(record.get("clean_text") or "")

    if context_chars <= 0:
        return title

    return " ".join([title, clean_text[:context_chars]])


def keyword_count(
    record: Dict[str, Any],
    keyword_pattern: Pattern,
    context_chars: int,
) -> int:
    text = keyword_search_text(record, context_chars)
    return len(keyword_pattern.findall(text))


def keyword_matches(
    record: Dict[str, Any],
    keyword_pattern: Pattern,
    context_chars: int,
) -> List[str]:
    text = keyword_search_text(record, context_chars)
    return sorted(set(match.lower() for match in keyword_pattern.findall(text)))


def add_records(
    selected: List[Dict[str, Any]],
    seen_urls: Set[str],
    candidates: List[Dict[str, Any]],
    limit: Optional[int] = None,
) -> int:
    added = 0

    for record in candidates:
        if limit is not None and added >= limit:
            break

        url = record.get("url")
        if not url or url in seen_urls:
            continue

        selected.append(record)
        seen_urls.add(url)
        added += 1

    return added


def sample_media_candidates(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    target_size: int,
    random_negative_target: int,
    high_score_threshold: float,
    medium_score_threshold: float,
    random_seed: int,
    keyword_context_chars: int,
    keywords: List[str],
) -> None:
    random.seed(random_seed)

    records = load_jsonl(input_path)
    keyword_pattern = build_keyword_pattern(keywords)

    high_score: List[Dict[str, Any]] = []
    medium_score: List[Dict[str, Any]] = []
    keyword_hits: List[Dict[str, Any]] = []
    random_negative_pool: List[Dict[str, Any]] = []

    for record in records:
        score = get_score(record)
        hits = keyword_count(record, keyword_pattern, keyword_context_chars)
        matches = keyword_matches(record, keyword_pattern, keyword_context_chars)

        record["sample_keyword_count"] = hits
        record["sample_keyword_matches"] = matches

        if score >= high_score_threshold:
            record["sample_group"] = "high_score"
            record["sample_reason"] = "score >= {}".format(high_score_threshold)
            high_score.append(record)
        elif score >= medium_score_threshold:
            record["sample_group"] = "medium_score"
            record["sample_reason"] = "score >= {}".format(medium_score_threshold)
            medium_score.append(record)
        elif hits > 0:
            record["sample_group"] = "keyword_hit_low_score"
            record["sample_reason"] = "keyword_hits={}, score < {}".format(
                hits,
                medium_score_threshold,
            )
            keyword_hits.append(record)
        else:
            record["sample_group"] = "random_negative"
            record["sample_reason"] = "no keyword hit, low score"
            random_negative_pool.append(record)

    high_score = sorted(high_score, key=get_score, reverse=True)
    medium_score = sorted(medium_score, key=get_score, reverse=True)
    keyword_hits = sorted(
        keyword_hits,
        key=lambda record: (
            record.get("sample_keyword_count", 0),
            get_score(record),
        ),
        reverse=True,
    )

    selected: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    high_added = add_records(selected, seen_urls, high_score)
    medium_added = add_records(selected, seen_urls, medium_score)

    keyword_slots = max(0, target_size - random_negative_target - len(selected))
    keyword_added = add_records(selected, seen_urls, keyword_hits, keyword_slots)

    remaining_slots = max(0, target_size - len(selected))
    random_candidates = [
        record
        for record in random_negative_pool
        if record.get("url") and record.get("url") not in seen_urls
    ]

    random_negatives = random.sample(
        random_candidates,
        min(remaining_slots, len(random_candidates)),
    )
    random_negative_added = add_records(selected, seen_urls, random_negatives)

    report = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "target_size": target_size,
        "selected_records": len(selected),
        "input_records": len(records),
        "random_seed": random_seed,
        "high_score_threshold": high_score_threshold,
        "medium_score_threshold": medium_score_threshold,
        "random_negative_target": random_negative_target,
        "keyword_context_chars": keyword_context_chars,
        "high_score_pool": len(high_score),
        "medium_score_pool": len(medium_score),
        "keyword_hit_pool": len(keyword_hits),
        "random_negative_pool": len(random_negative_pool),
        "high_score_selected": high_added,
        "medium_score_selected": medium_added,
        "keyword_hit_selected": keyword_added,
        "random_negative_selected": random_negative_added,
        "sample_group_counts": dict(Counter(record.get("sample_group") for record in selected)),
        "source_counts": dict(Counter(record.get("source_id") for record in selected)),
        "keywords": keywords,
    }

    write_jsonl(output_path, selected)
    write_json(report_path, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sample scored media candidates for annotation."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--target-size", type=int, default=70)
    parser.add_argument("--random-negative-target", type=int, default=15)
    parser.add_argument("--high-score-threshold", type=float, default=0.20)
    parser.add_argument("--medium-score-threshold", type=float, default=0.10)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--keyword-context-chars",
        type=int,
        default=1200,
        help="Number of clean_text characters used for keyword matching after the title. Use 0 for title only.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    sample_media_candidates(
        input_path=Path(args.input),
        output_path=Path(args.output),
        report_path=Path(args.report),
        target_size=args.target_size,
        random_negative_target=args.random_negative_target,
        high_score_threshold=args.high_score_threshold,
        medium_score_threshold=args.medium_score_threshold,
        random_seed=args.random_seed,
        keyword_context_chars=args.keyword_context_chars,
        keywords=DEFAULT_KEYWORDS,
    )