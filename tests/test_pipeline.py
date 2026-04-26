from changescout.pipeline import run_scoring_and_decision


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