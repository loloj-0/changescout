from pathlib import Path

from changescout.pipeline import (
    build_operational_run_paths,
    run_scoring_and_decision,
)


def test_pipeline_adds_decision():
    config = {
        "rule_scoring": {
            "weight": 1.0,
            "weights": {
                "structural": 1.0,
                "soft": 0.0,
                "title_multiplier": 1.0,
            },
            "structural_keywords": ["test"],
        },
        "pattern_scoring": {
            "weights": {
                "strong_positive": 2.0,
                "weak_positive": 0.4,
                "negative": -0.1,
                "review": 0.0,
            },
            "strong_positive_patterns": [],
            "weak_positive_patterns": [],
            "negative_patterns": [],
            "review_patterns": [],
            "pattern_score_cap": 5.0,
            "pattern_score_floor": -2.0,
        },
        "retrieval_scoring": {
            "enabled": False,
            "weight": 0.0,
        },
    }

    docs = [
        {
            "title": "test",
            "clean_text": "",
            "filter_signals": {
                "structural_change_hits": ["test"],
                "soft_change_hits": [],
            },
        }
    ]

    result = run_scoring_and_decision(docs, config)

    assert "decision" in result[0]


def test_build_operational_run_paths_are_run_scoped():
    paths = build_operational_run_paths(
        run_id="issue24_test",
        output_root=Path("artifacts/runs"),
        html_root=Path("data/crawling"),
    )

    assert paths.run_dir == Path("artifacts/runs/issue24_test")
    assert paths.discovery_path == Path("artifacts/runs/issue24_test/discovery.jsonl")
    assert paths.crawl_path == Path("artifacts/runs/issue24_test/crawl.jsonl")
    assert paths.cleaned_path == Path("artifacts/runs/issue24_test/cleaned.jsonl")
    assert paths.excluded_path == Path("artifacts/runs/issue24_test/excluded.jsonl")
    assert paths.filtered_path == Path("artifacts/runs/issue24_test/filtered.jsonl")
    assert paths.filtered_excluded_path == Path("artifacts/runs/issue24_test/filtered_excluded.jsonl")
    assert paths.scored_path == Path("artifacts/runs/issue24_test/scored.jsonl")
    assert paths.leads_jsonl_path == Path("artifacts/runs/issue24_test/leads.jsonl")
    assert paths.leads_csv_path == Path("artifacts/runs/issue24_test/leads.csv")
    assert paths.leads_with_locations_jsonl_path == Path("artifacts/runs/issue24_test/leads_with_locations.jsonl")
    assert paths.leads_with_locations_csv_path == Path("artifacts/runs/issue24_test/leads_with_locations.csv")
    assert paths.leads_with_geoadmin_locations_jsonl_path == Path("artifacts/runs/issue24_test/leads_with_geoadmin_locations.jsonl")
    assert paths.leads_with_geoadmin_locations_csv_path == Path("artifacts/runs/issue24_test/leads_with_geoadmin_locations.csv")
    assert paths.reports_dir == Path("artifacts/runs/issue24_test/reports")
    assert paths.metadata_dir == Path("artifacts/runs/issue24_test/metadata")
    assert paths.logs_dir == Path("artifacts/runs/issue24_test/logs")
    assert paths.run_metadata_path == Path("artifacts/runs/issue24_test/metadata/run_metadata.json")
    assert paths.run_log_path == Path("artifacts/runs/issue24_test/logs/run.log")


def test_operational_run_paths_do_not_point_to_evaluation_outputs():
    paths = build_operational_run_paths(
        run_id="issue24_test",
        output_root=Path("artifacts/runs"),
        html_root=Path("data/crawling"),
    )

    all_paths = [
        paths.scope_snapshot_path,
        paths.discovery_path,
        paths.crawl_path,
        paths.cleaned_path,
        paths.excluded_path,
        paths.filtered_path,
        paths.filtered_excluded_path,
        paths.scored_path,
        paths.leads_jsonl_path,
        paths.leads_csv_path,
        paths.discovery_report_path,
        paths.crawl_report_path,
        paths.cleaning_report_path,
        paths.filter_report_path,
        paths.scoring_report_path,
        paths.lead_generation_report_path,
        paths.location_hinting_report_path,
        paths.geoadmin_location_hinting_report_path,
        paths.run_metadata_path,
        paths.run_log_path,
    ]

    for path in all_paths:
        assert "data/annotation/evaluation" not in str(path)


def test_operational_run_paths_keep_html_storage_separate():
    paths = build_operational_run_paths(
        run_id="issue24_test",
        output_root=Path("artifacts/runs"),
        html_root=Path("data/crawling"),
    )

    assert paths.html_base_dir == Path("data/crawling")
    assert paths.html_base_dir != paths.run_dir
