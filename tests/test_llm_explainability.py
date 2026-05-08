from __future__ import annotations

import json
from pathlib import Path

from changescout.ml.llm_explainability import (
    build_prompt,
    extract_json,
    prepare_explainability_records,
    validate_explanation_output,
)


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_extract_json_from_fenced_output():
    raw_output = (
        "```json\n"
        '{"evidence_type": "confirmed_geometry", "evidence_snippet": "neuer Radweg"}\n'
        "```"
    )

    parsed, error = extract_json(raw_output)

    assert error == ""
    assert parsed["evidence_type"] == "confirmed_geometry"


def test_validate_explanation_output_flags_supported_snippet():
    source_text = "Mit dem Projekt wird ein neuer Radweg gebaut."

    output = validate_explanation_output(
        parsed={
            "evidence_type": "confirmed_geometry",
            "explanation_note": "Konkreter neuer Radweg.",
            "evidence_snippet": "neuer Radweg",
            "geometry_signal": "neuer Radweg",
            "audit_warning": "",
        },
        source_text=source_text,
    )

    assert output["evidence_type"] == "confirmed_geometry"
    assert output["evidence_snippet_found_in_source"] is True
    assert output["requires_manual_check"] is False


def test_validate_explanation_output_flags_missing_or_unsupported_snippet():
    source_text = "Die Strasse wird saniert."

    output = validate_explanation_output(
        parsed={
            "evidence_type": "confirmed_geometry",
            "explanation_note": "Nicht belegte Aussage.",
            "evidence_snippet": "neue Umfahrung",
            "geometry_signal": "Umfahrung",
            "audit_warning": "",
        },
        source_text=source_text,
    )

    assert output["evidence_snippet_found_in_source"] is False
    assert output["requires_manual_check"] is True


def test_prepare_explainability_records_merges_source_text_from_scored(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "runs" / "llm_test"

    write_jsonl(
        run_dir / "leads.jsonl",
        [
            {
                "rank": 1,
                "title": "Lead",
                "url": "https://example.test/project",
                "source_id": "test_source",
                "selection_reason": "thematic_score >= 0.1",
            }
        ],
    )

    write_jsonl(
        run_dir / "scored.jsonl",
        [
            {
                "title": "Lead",
                "url": "https://example.test/project/",
                "clean_text": "Mit dem Projekt wird ein neuer Radweg gebaut.",
            }
        ],
    )

    input_path, records = prepare_explainability_records(run_dir)

    assert input_path == run_dir / "leads.jsonl"
    assert len(records) == 1
    assert "neuer Radweg" in records[0]["llm_source_text"]


def test_build_prompt_contains_review_guardrails():
    prompt = build_prompt(
        {
            "title": "Test",
            "source_id": "source",
            "selection_reason": "tfidf_actionable_probability >= 0.5",
            "llm_source_text": "Mit dem Projekt wird ein neuer Radweg gebaut.",
        }
    )

    assert "Your task is not to remove the lead." in prompt
    assert "Return only JSON" in prompt
    assert "confirmed_geometry" in prompt
    assert "neuer Radweg" in prompt
