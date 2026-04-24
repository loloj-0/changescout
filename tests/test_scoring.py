from changescout.scoring import score_document, score_documents


def test_structural_hits_increase_rule_score():
    config = {
        "rule_scoring": {
            "weight": 0.6,
            "weights": {
                "structural": 1.0,
                "soft": -0.2,
                "title_multiplier": 2.5,
            },
            "structural_keywords": ["strassenprojekt"],
        },
        "retrieval_scoring": {
            "enabled": False,
            "weight": 0.4,
        },
    }

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
    config = {
        "rule_scoring": {
            "weight": 0.6,
            "weights": {
                "structural": 1.0,
                "soft": -0.2,
                "title_multiplier": 2.5,
            },
            "structural_keywords": [],
        },
        "retrieval_scoring": {
            "enabled": False,
            "weight": 0.4,
        },
    }

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


def test_bm25_retrieval_score_contributes_to_thematic_score():
    config = {
        "rule_scoring": {
            "weight": 0.6,
            "weights": {
                "structural": 1.0,
                "soft": -0.2,
                "title_multiplier": 2.5,
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

    assert scored_documents[0]["scoring_signals"]["retrieval_score"] > scored_documents[1]["scoring_signals"]["retrieval_score"]
    assert scored_documents[0]["thematic_score"] > scored_documents[1]["thematic_score"]


def test_scoring_preserves_document_fields():
    config = {
        "rule_scoring": {
            "weight": 0.6,
            "weights": {
                "structural": 1.0,
                "soft": -0.2,
                "title_multiplier": 2.5,
            },
            "structural_keywords": ["strassenprojekt"],
        },
        "retrieval_scoring": {
            "enabled": False,
            "weight": 0.4,
        },
    }

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