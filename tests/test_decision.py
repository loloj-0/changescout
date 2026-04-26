from changescout.decision import classify_document


def test_decision_include():
    doc = {"thematic_score": 0.7}
    result = classify_document(doc)
    assert result["decision"] == "include"


def test_decision_review():
    doc = {"thematic_score": 0.4}
    result = classify_document(doc)
    assert result["decision"] == "review"


def test_decision_exclude():
    doc = {"thematic_score": 0.1}
    result = classify_document(doc)
    assert result["decision"] == "exclude"


# --- CRITICAL: threshold tests ---


def test_decision_include_boundary():
    doc = {"thematic_score": 0.55}
    result = classify_document(doc)
    assert result["decision"] == "include"


def test_decision_review_boundary():
    doc = {"thematic_score": 0.20}
    result = classify_document(doc)
    assert result["decision"] == "review"


def test_decision_exclude_boundary():
    doc = {"thematic_score": 0.199}
    result = classify_document(doc)
    assert result["decision"] == "exclude"