from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

import pandas as pd


DEFAULT_LEAD_THRESHOLD = 0.10
DEFAULT_PREVIEW_LENGTH = 500


REQUIRED_SCORED_COLUMNS = {
    "document_id",
    "source_id",
    "url",
    "title",
    "clean_text",
    "thematic_score",
}


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


def load_scored_documents(path: Path) -> pd.DataFrame:
    records = load_jsonl(path)
    scored = pd.DataFrame(records)

    missing_columns = REQUIRED_SCORED_COLUMNS - set(scored.columns)
    if missing_columns:
        raise ValueError(f"Missing scored columns: {sorted(missing_columns)}")

    scored = scored.copy()
    scored["thematic_score"] = scored["thematic_score"].astype(float)

    return scored


def load_classifier_predictions(path: Path) -> pd.DataFrame:
    predictions = pd.read_csv(path)

    required_columns = {
        "url",
        "classifier_prediction",
        "classifier_probability",
    }

    missing_columns = required_columns - set(predictions.columns)
    if missing_columns:
        raise ValueError(
            f"Missing classifier prediction columns: {sorted(missing_columns)}"
        )

    return predictions[
        [
            "url",
            "classifier_prediction",
            "classifier_probability",
        ]
    ].copy()


def enrich_with_classifier_predictions(
    scored: pd.DataFrame,
    predictions: Optional[pd.DataFrame],
) -> pd.DataFrame:
    if predictions is None:
        return scored.copy()

    enriched = scored.merge(
        predictions,
        on="url",
        how="left",
    )

    return enriched


def make_text_preview(text: Any, max_length: int = DEFAULT_PREVIEW_LENGTH) -> str:
    if text is None:
        return ""

    preview = " ".join(str(text).split())

    if len(preview) <= max_length:
        return preview

    return preview[:max_length].rstrip()


def generate_leads(
    documents: pd.DataFrame,
    threshold: float = DEFAULT_LEAD_THRESHOLD,
    preview_length: int = DEFAULT_PREVIEW_LENGTH,
) -> pd.DataFrame:
    leads = documents[documents["thematic_score"] >= threshold].copy()

    leads["lead_reason"] = f"thematic_score >= {threshold:.2f}"
    leads["text_preview"] = leads["clean_text"].map(
        lambda text: make_text_preview(text, max_length=preview_length)
    )

    output_columns = [
        "document_id",
        "source_id",
        "url",
        "title",
        "thematic_score",
        "lead_reason",
        "classifier_prediction",
        "classifier_probability",
        "text_preview",
    ]

    available_output_columns = [
        column for column in output_columns if column in leads.columns
    ]

    leads = leads[available_output_columns].copy()

    leads = leads.sort_values(
        by=["thematic_score", "title", "url"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    return leads


def build_lead_generation_report(
    documents: pd.DataFrame,
    leads: pd.DataFrame,
    threshold: float,
) -> Dict[str, Any]:
    scores = documents["thematic_score"].astype(float)

    return {
        "input_documents": int(len(documents)),
        "lead_count": int(len(leads)),
        "threshold": threshold,
        "min_score": float(scores.min()) if len(scores) else None,
        "max_score": float(scores.max()) if len(scores) else None,
        "mean_score": float(scores.mean()) if len(scores) else None,
    }


def dataframe_to_records(dataframe: pd.DataFrame) -> List[Dict[str, Any]]:
    return dataframe.where(pd.notnull(dataframe), None).to_dict(orient="records")


def run_lead_generation(
    scored_path: Path,
    output_jsonl_path: Path,
    output_csv_path: Path,
    report_output_path: Path,
    classifier_predictions_path: Optional[Path] = None,
    threshold: float = DEFAULT_LEAD_THRESHOLD,
    preview_length: int = DEFAULT_PREVIEW_LENGTH,
) -> Dict[str, Any]:
    scored = load_scored_documents(scored_path)

    predictions = None
    if classifier_predictions_path is not None and classifier_predictions_path.exists():
        predictions = load_classifier_predictions(classifier_predictions_path)

    enriched = enrich_with_classifier_predictions(scored, predictions)
    leads = generate_leads(
        enriched,
        threshold=threshold,
        preview_length=preview_length,
    )

    records = dataframe_to_records(leads)

    write_jsonl(output_jsonl_path, records)

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    leads.to_csv(output_csv_path, index=False, encoding="utf-8")

    report = build_lead_generation_report(
        documents=enriched,
        leads=leads,
        threshold=threshold,
    )
    write_json(report_output_path, report)

    return report