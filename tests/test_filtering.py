from changescout.filtering import apply_hard_filter


def test_title_blacklist_excludes_document():
    config = {
        "hard_exclusion": {
            "title_keywords": ["event"],
            "url_keywords": [],
        }
    }

    document = {
        "title": "Music Event",
        "url": "https://example.org/music-event",
    }

    included, excluded = apply_hard_filter(document, config)

    assert included is None
    assert excluded is not None
    assert excluded["reason"] == "blacklist_title"
    assert excluded["matched_rule"] == "event"


def test_url_blacklist_excludes_document():
    config = {
        "hard_exclusion": {
            "title_keywords": [],
            "url_keywords": ["/jobs"],
        }
    }

    document = {
        "title": "Open positions",
        "url": "https://example.org/jobs/data-scientist",
    }

    included, excluded = apply_hard_filter(document, config)

    assert included is None
    assert excluded is not None
    assert excluded["reason"] == "blacklist_url"
    assert excluded["matched_rule"] == "/jobs"


def test_infrastructure_document_passes_filter():
    config = {
        "hard_exclusion": {
            "title_keywords": ["event"],
            "url_keywords": ["/jobs"],
        }
    }

    document = {
        "title": "Strassenprojekt Zürich",
        "url": "https://example.org/tiefbau/strassenprojekt-zuerich",
    }

    included, excluded = apply_hard_filter(document, config)

    assert included == document
    assert excluded is None