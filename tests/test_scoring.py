from changescout.scoring import score_document, score_documents


def base_config(pattern_scoring=None, retrieval_enabled=False):
    config = {
        "rule_scoring": {
            "weight": 0.6,
            "weights": {
                "structural": 0.8,
                "soft": -0.1,
                "title_multiplier": 1.2,
            },
            "structural_keywords": ["strassenprojekt"],
        },
        "retrieval_scoring": {
            "enabled": retrieval_enabled,
            "weight": 0.4,
        },
    }

    if pattern_scoring is not None:
        config["pattern_scoring"] = pattern_scoring

    return config


def test_structural_hits_increase_rule_score():
    config = base_config()

    document = {
        "title": "Strassenprojekt Zürich",
        "filter_signals": {
            "structural_change_hits": ["ausbau", "brücke"],
            "soft_change_hits": [],
        },
    }

    scored = score_document(document, config)

    assert scored["thematic_score"] > 0
    assert scored["scoring_signals"]["rule_score"] > 0


def test_soft_hits_reduce_rule_score():
    config = base_config()

    stronger_document = {
        "title": "Test",
        "filter_signals": {
            "structural_change_hits": ["ausbau", "brücke"],
            "soft_change_hits": [],
        },
    }

    weaker_document = {
        "title": "Test",
        "filter_signals": {
            "structural_change_hits": ["ausbau", "brücke"],
            "soft_change_hits": ["baustelle", "sperrung"],
        },
    }

    stronger_score = score_document(stronger_document, config)["scoring_signals"]["rule_score"]
    weaker_score = score_document(weaker_document, config)["scoring_signals"]["rule_score"]

    assert weaker_score < stronger_score


def test_pattern_hits_contribute_to_rule_score():
    config = base_config(
        pattern_scoring={
            "weights": {
                "strong_positive": 2.0,
                "weak_positive": 0.4,
                "negative": -0.1,
                "review": 0.0,
            },
            "pattern_score_cap": 5.0,
            "pattern_score_floor": -2.0,
            "strong_positive_patterns": [
                "neue\\s+strasse",
                "unterführung.*ersetzt",
            ],
            "weak_positive_patterns": [
                "mittelschutzinsel",
            ],
            "negative_patterns": [
                "belag",
            ],
            "review_patterns": [
                "ersatzbau",
            ],
        }
    )

    document = {
        "title": "Test",
        "clean_text": "Eine neue Strasse wird gebaut.",
        "filter_signals": {
            "structural_change_hits": [],
            "soft_change_hits": [],
        },
    }

    scored = score_document(document, config)
    signals = scored["scoring_signals"]

    assert scored["thematic_score"] > 0
    assert signals["rule_score"] > 0
    assert signals["pattern_raw_score"] > 0
    assert signals["strong_pattern_hits"] == ["neue\\s+strasse"]


def test_pattern_hits_are_deduplicated():
    config = base_config(
        pattern_scoring={
            "weights": {
                "strong_positive": 2.0,
                "weak_positive": 0.4,
                "negative": -0.1,
                "review": 0.0,
            },
            "pattern_score_cap": 5.0,
            "pattern_score_floor": -2.0,
            "strong_positive_patterns": [
                "neue\\s+strasse",
            ],
            "weak_positive_patterns": [],
            "negative_patterns": [],
            "review_patterns": [],
        }
    )

    document = {
        "title": "Test",
        "clean_text": "Eine neue Strasse wird gebaut. Diese neue Strasse ist wichtig.",
        "filter_signals": {
            "structural_change_hits": [],
            "soft_change_hits": [],
        },
    }

    scored = score_document(document, config)
    signals = scored["scoring_signals"]

    assert signals["strong_pattern_hits"] == ["neue\\s+strasse"]
    assert signals["pattern_raw_score"] == 2.0


def test_pattern_score_is_capped():
    config = base_config(
        pattern_scoring={
            "weights": {
                "strong_positive": 2.0,
                "weak_positive": 0.4,
                "negative": -0.1,
                "review": 0.0,
            },
            "pattern_score_cap": 5.0,
            "pattern_score_floor": -2.0,
            "strong_positive_patterns": [
                "neue\\s+strasse",
                "neue\\s+verbindung",
                "umfahrung",
            ],
            "weak_positive_patterns": [
                "mittelschutzinsel",
                "querungshilfe",
            ],
            "negative_patterns": [],
            "review_patterns": [],
        }
    )

    document = {
        "title": "Test",
        "clean_text": (
            "Eine neue Strasse und eine neue Verbindung werden gebaut. "
            "Die Umfahrung enthält eine Mittelschutzinsel und eine Querungshilfe."
        ),
        "filter_signals": {
            "structural_change_hits": [],
            "soft_change_hits": [],
        },
    }

    scored = score_document(document, config)

    assert scored["scoring_signals"]["pattern_raw_score"] == 5.0


def test_negative_pattern_reduces_rule_score_mildly():
    config = base_config(
        pattern_scoring={
            "weights": {
                "strong_positive": 2.0,
                "weak_positive": 0.4,
                "negative": -0.1,
                "review": 0.0,
            },
            "pattern_score_cap": 5.0,
            "pattern_score_floor": -2.0,
            "strong_positive_patterns": [
                "neue\\s+strasse",
            ],
            "weak_positive_patterns": [],
            "negative_patterns": [
                "belag",
            ],
            "review_patterns": [],
        }
    )

    positive_document = {
        "title": "Test",
        "clean_text": "Eine neue Strasse wird gebaut.",
        "filter_signals": {
            "structural_change_hits": [],
            "soft_change_hits": [],
        },
    }

    mixed_document = {
        "title": "Test",
        "clean_text": "Eine neue Strasse wird gebaut. Der Belag wird erneuert.",
        "filter_signals": {
            "structural_change_hits": [],
            "soft_change_hits": [],
        },
    }

    positive_score = score_document(positive_document, config)["scoring_signals"]["rule_score"]
    mixed_score = score_document(mixed_document, config)["scoring_signals"]["rule_score"]

    assert mixed_score < positive_score


def test_bm25_retrieval_score_contributes_to_thematic_score():
    config = {
        "rule_scoring": {
            "weight": 0.6,
            "weights": {
                "structural": 0.8,
                "soft": -0.1,
                "title_multiplier": 1.2,
            },
            "structural_keywords": [],
        },
        "retrieval_scoring": {
            "enabled": True,
            "method": "bm25",
            "weight": 0.4,
            "query_terms": ["brücke"],
            "bm25": {
                "k1": 1.5,
                "b": 0.75,
            },
        },
    }

    matching_document = {
        "title": "Brücke Projekt",
        "clean_text": "brücke brücke brücke",
        "filter_signals": {
            "structural_change_hits": [],
            "soft_change_hits": [],
        },
    }

    non_matching_document = {
        "title": "Test",
        "clean_text": "verwaltung dokument ohne treffende begriffe",
        "filter_signals": {
            "structural_change_hits": [],
            "soft_change_hits": [],
        },
    }

    scored_documents = score_documents(
        [matching_document, non_matching_document],
        config,
    )

    assert (
        scored_documents[0]["scoring_signals"]["retrieval_score"]
        > scored_documents[1]["scoring_signals"]["retrieval_score"]
    )
    assert scored_documents[0]["thematic_score"] > scored_documents[1]["thematic_score"]


def test_scoring_preserves_document_fields():
    config = base_config()

    document = {
        "document_id": "doc-1",
        "title": "Strassenprojekt Zürich",
        "url": "https://example.org/project",
        "filter_signals": {
            "structural_change_hits": ["ausbau"],
            "soft_change_hits": [],
        },
    }

    scored = score_document(document, config)

    assert scored["document_id"] == "doc-1"
    assert scored["url"] == "https://example.org/project"
    assert "thematic_score" in scored
    assert "scoring_signals" in scored
    assert "rule_score" in scored["scoring_signals"]
    assert "retrieval_score" in scored["scoring_signals"]
    assert "pattern_raw_score" in scored["scoring_signals"]