from typing import Any, Dict, List

from changescout.decision import classify_document
from changescout.scoring import score_documents


def run_scoring_and_decision(
    documents: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    scored_documents = score_documents(documents, config)
    return [classify_document(document) for document in scored_documents]