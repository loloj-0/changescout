from pathlib import Path
from typing import Any, Dict, List
import json
import math
import re
from collections import Counter

import yaml


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_scoring_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("scoring config must be a YAML mapping")

    return data


def tokenize(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.casefold())


def normalize_score(raw_score: float) -> float:
    if raw_score <= 0:
        return 0.0

    return min(raw_score / 10.0, 1.0)


def min_max_normalize(scores: List[float]) -> List[float]:
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [0.0 for _ in scores]

    return [
        (score - min_score) / (max_score - min_score)
        for score in scores
    ]


def get_rule_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get("rule_scoring", {})


def get_retrieval_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get("retrieval_scoring", {})


def find_title_structural_hits(
    document: Dict[str, Any],
    config: Dict[str, Any],
) -> List[str]:
    rule_config = get_rule_config(config)
    title = str(document.get("title", "")).casefold()
    structural_keywords = rule_config.get("structural_keywords", [])

    if not isinstance(structural_keywords, list):
        raise ValueError("rule_scoring.structural_keywords must be a list")

    return [
        keyword
        for keyword in structural_keywords
        if str(keyword).casefold() in title
    ]


def compute_rule_raw_score(
    structural_hits: List[str],
    soft_hits: List[str],
    title_structural_hits: List[str],
    config: Dict[str, Any],
) -> float:
    rule_config = get_rule_config(config)
    weights = rule_config.get("weights", {})

    structural_weight = float(weights.get("structural", 1.0))
    soft_weight = float(weights.get("soft", -0.2))
    title_multiplier = float(weights.get("title_multiplier", 2.5))

    structural_score = len(structural_hits) * structural_weight
    soft_score = len(soft_hits) * soft_weight
    title_boost = len(title_structural_hits) * structural_weight * title_multiplier

    return structural_score + soft_score + title_boost


def compute_rule_score(
    document: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    filter_signals = document.get("filter_signals", {})

    structural_hits = filter_signals.get("structural_change_hits", [])
    soft_hits = filter_signals.get("soft_change_hits", [])
    title_structural_hits = find_title_structural_hits(document, config)

    raw_score = compute_rule_raw_score(
        structural_hits=structural_hits,
        soft_hits=soft_hits,
        title_structural_hits=title_structural_hits,
        config=config,
    )

    return {
        "rule_score": normalize_score(raw_score),
        "rule_raw_score": raw_score,
        "structural_hits": structural_hits,
        "soft_hits": soft_hits,
        "title_structural_hits": title_structural_hits,
    }


def compute_bm25_scores(
    documents: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    retrieval_config = get_retrieval_config(config)

    if not retrieval_config.get("enabled", False):
        return [
            {
                "retrieval_score": 0.0,
                "retrieval_raw_score": 0.0,
                "retrieval_query_terms": [],
            }
            for _ in documents
        ]

    query_terms = [
        str(term).casefold()
        for term in retrieval_config.get("query_terms", [])
    ]

    bm25_config = retrieval_config.get("bm25", {})
    k1 = float(bm25_config.get("k1", 1.5))
    b = float(bm25_config.get("b", 0.75))

    tokenized_documents = [
        tokenize(f"{document.get('title', '')} {document.get('clean_text', '')}")
        for document in documents
    ]

    document_lengths = [len(tokens) for tokens in tokenized_documents]
    avg_document_length = (
        sum(document_lengths) / len(document_lengths)
        if document_lengths
        else 0.0
    )

    document_count = len(tokenized_documents)

    document_frequencies: Dict[str, int] = {}
    for term in query_terms:
        document_frequencies[term] = sum(
            1 for tokens in tokenized_documents if term in tokens
        )

    raw_scores: List[float] = []

    for tokens, doc_length in zip(tokenized_documents, document_lengths):
        term_counts = Counter(tokens)
        score = 0.0

        for term in query_terms:
            term_frequency = term_counts.get(term, 0)
            if term_frequency == 0:
                continue

            document_frequency = document_frequencies.get(term, 0)
            idf = math.log(
                1
                + (document_count - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )

            denominator = (
                term_frequency
                + k1 * (1 - b + b * doc_length / avg_document_length)
                if avg_document_length > 0
                else term_frequency + k1
            )

            score += idf * (
                term_frequency * (k1 + 1)
            ) / denominator

        raw_scores.append(score)

    normalized_scores = min_max_normalize(raw_scores)

    return [
        {
            "retrieval_score": normalized_score,
            "retrieval_raw_score": raw_score,
            "retrieval_query_terms": query_terms,
        }
        for raw_score, normalized_score in zip(raw_scores, normalized_scores)
    ]


def combine_scores(
    rule_score: float,
    retrieval_score: float,
    config: Dict[str, Any],
) -> float:
    rule_weight = float(get_rule_config(config).get("weight", 0.6))
    retrieval_weight = float(get_retrieval_config(config).get("weight", 0.4))

    combined = rule_score * rule_weight + retrieval_score * retrieval_weight

    return max(0.0, min(combined, 1.0))


def score_documents(
    documents: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    retrieval_scores = compute_bm25_scores(documents, config)
    scored_documents = []

    for document, retrieval_signal in zip(documents, retrieval_scores):
        rule_signal = compute_rule_score(document, config)

        thematic_score = combine_scores(
            rule_score=rule_signal["rule_score"],
            retrieval_score=retrieval_signal["retrieval_score"],
            config=config,
        )

        scored_document = dict(document)
        scored_document["thematic_score"] = thematic_score
        scored_document["scoring_signals"] = {
            **rule_signal,
            **retrieval_signal,
        }

        scored_documents.append(scored_document)

    return scored_documents


def score_document(
    document: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    return score_documents([document], config)[0]


def build_score_buckets(scored_documents: List[Dict[str, Any]]) -> Dict[str, int]:
    buckets = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0,
    }

    for document in scored_documents:
        score = float(document["thematic_score"])

        if score < 0.2:
            buckets["0.0-0.2"] += 1
        elif score < 0.4:
            buckets["0.2-0.4"] += 1
        elif score < 0.6:
            buckets["0.4-0.6"] += 1
        elif score < 0.8:
            buckets["0.6-0.8"] += 1
        else:
            buckets["0.8-1.0"] += 1

    return buckets


def build_scoring_report(scored_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    scores = [float(document["thematic_score"]) for document in scored_documents]
    rule_scores = [
        float(document["scoring_signals"]["rule_score"])
        for document in scored_documents
    ]
    retrieval_scores = [
        float(document["scoring_signals"]["retrieval_score"])
        for document in scored_documents
    ]
    retrieval_raw_scores = [
        float(document["scoring_signals"]["retrieval_raw_score"])
        for document in scored_documents
    ]

    if not scores:
        return {
            "total_documents": 0,
            "min_score": None,
            "max_score": None,
            "mean_score": None,
            "mean_rule_score": None,
            "mean_retrieval_score": None,
            "min_retrieval_raw_score": None,
            "max_retrieval_raw_score": None,
            "score_buckets": build_score_buckets([]),
        }

    return {
        "total_documents": len(scored_documents),
        "min_score": min(scores),
        "max_score": max(scores),
        "mean_score": sum(scores) / len(scores),
        "mean_rule_score": sum(rule_scores) / len(rule_scores),
        "mean_retrieval_score": sum(retrieval_scores) / len(retrieval_scores),
        "min_retrieval_raw_score": min(retrieval_raw_scores),
        "max_retrieval_raw_score": max(retrieval_raw_scores),
        "score_buckets": build_score_buckets(scored_documents),
    }


def run_scoring(
    input_path: Path,
    config_path: Path,
    output_path: Path,
    report_output_path: Path,
) -> Dict[str, Any]:
    config = load_scoring_config(config_path)
    documents = load_jsonl(input_path)

    scored_documents = score_documents(documents, config)

    write_jsonl(output_path, scored_documents)

    report = build_scoring_report(scored_documents)
    write_json(report_output_path, report)

    return report


if __name__ == "__main__":
    report = run_scoring(
        input_path=Path("artifacts/filtered.jsonl"),
        config_path=Path("config/scoring.yaml"),
        output_path=Path("artifacts/scored.jsonl"),
        report_output_path=Path("artifacts/scoring_report.json"),
    )

    print("Thematic scoring completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))