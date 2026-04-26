from typing import Any, Dict


def classify_document(document: Dict[str, Any]) -> Dict[str, Any]:
    score = float(document["thematic_score"])

    if score >= 0.55:
        decision = "include"
    elif score >= 0.20:
        decision = "review"
    else:
        decision = "exclude"

    result = dict(document)
    result["decision"] = decision

    return result