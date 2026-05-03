from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List
import hashlib
import json
import re

import requests


GEOADMIN_SEARCH_URL = "https://api3.geo.admin.ch/rest/services/ech/SearchServer"

DEFAULT_ORIGINS = "gazetteer,gg25"
DEFAULT_LIMIT = 5
DEFAULT_SR = 2056
DEFAULT_TIMEOUT_SECONDS = 10
MAX_QUERY_WORDS = 10
MAX_QUERY_CANDIDATES = 5
MAX_TEXT_CHARS = 1500
MAX_TEXT_QUERY_CANDIDATES = 5

GENERIC_QUERY_TOKENS = {
    "ab",
    "am",
    "an",
    "and",
    "auf",
    "aus",
    "bei",
    "bis",
    "das",
    "der",
    "die",
    "ein",
    "eine",
    "einer",
    "eines",
    "für",
    "fuer",
    "im",
    "in",
    "mit",
    "nach",
    "und",
    "vom",
    "von",
    "zur",
    "abschnitt",
    "ausbau",
    "baustelle",
    "brücke",
    "bruecke",
    "entwicklung",
    "ersatz",
    "geh",
    "instandsetzung",
    "kantonsstrasse",
    "kantonsstrassen",
    "kreisel",
    "knoten",
    "lv",
    "management",
    "markierung",
    "massnahme",
    "massnahmen",
    "maßnahme",
    "maßnahmen",
    "mitwirkung",
    "neue",
    "neubau",
    "ortsdurchfahrt",
    "planauflage",
    "projekt",
    "projekte",
    "radweg",
    "raum",
    "regeln",
    "sanierung",
    "sbb",
    "signalisation",
    "strasse",
    "strassen",
    "strassenprojekt",
    "tiefbau",
    "unterführung",
    "unterfuehrung",
    "ueberführung",
    "ueberfuehrung",
    "überführung",
    "verbesserung",
    "verbreiterung",
    "verkehr",
    "verkehrsinfrastruktur",
    "veloweg",
}

TEXT_CANDIDATE_EXCLUSION_TOKENS = GENERIC_QUERY_TOKENS | {
    "aktuell",
    "antworten",
    "bau",
    "belag",
    "download",
    "drucken",
    "fragen",
    "gemeinde",
    "informationen",
    "kontakt",
    "konzept",
    "publiziert",
    "seite",
    "stand",
    "uebersicht",
    "uhr",
    "übersicht",
    "ziele",
}

GENERIC_QUERY_SUFFIXES = (
    "strasse",
    "strassen",
    "straße",
    "weg",
    "platz",
    "gasse",
    "allee",
    "ring",
    "quai",
)

PREFERRED_OBJECT_TYPE_PRIORITIES = {
    "Ort": 1,
    "Quartierteil": 2,
    "Gebiet": 3,
    "Flurname swisstopo": 4,
    "Strasse": 6,
    "Brücke": 6,
    "Tunnel": 6,
    "Unterführung": 6,
    "Bahnhof": 6,
    "Haltestelle": 6,
    "Turm": 8,
}

LOW_PRIORITY_OBJECT_TYPES = {
    "Grossregion",
    "Gebaeude",
    "Gebäude",
    "Schul- und Hochschulareal",
}


@dataclass(frozen=True)
class GeoAdminQuery:
    search_text: str
    origins: str = DEFAULT_ORIGINS
    limit: int = DEFAULT_LIMIT
    sr: int = DEFAULT_SR

    def cache_key(self) -> str:
        payload = {
            "search_text": self.search_text,
            "origins": self.origins,
            "limit": self.limit,
            "sr": self.sr,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_query_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+[-–—]\s+", " ", text)
    text = re.sub(r"\s*/\s*", " ", text)
    text = re.sub(r"\s*,\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def strip_html(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(value))
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_object_type_from_label(value: Any) -> str:
    if value is None:
        return ""

    match = re.search(r"<i>(.*?)</i>", str(value))

    if not match:
        return ""

    return strip_html(match.group(1))


def trim_query_to_word_limit(query: str, max_words: int = MAX_QUERY_WORDS) -> str:
    words = query.split()

    if len(words) <= max_words:
        return query

    return " ".join(words[:max_words])


def raw_tokens(text: str) -> List[str]:
    normalized = normalize_query_text(text).casefold()
    return re.findall(r"[a-zäöüéèà0-9]{3,}", normalized)


def tokenize_query(text: str) -> List[str]:
    return [
        token
        for token in raw_tokens(text)
        if token not in GENERIC_QUERY_TOKENS
    ]


def is_useful_query_candidate(candidate: str) -> bool:
    candidate = normalize_query_text(candidate)
    all_tokens = raw_tokens(candidate)
    useful_tokens = tokenize_query(candidate)

    if not useful_tokens:
        return False

    if len(candidate) < 4:
        return False

    has_generic_tokens = any(token in GENERIC_QUERY_TOKENS for token in all_tokens)

    if len(useful_tokens) == 1:
        token = useful_tokens[0]

        if any(token.endswith(suffix) for suffix in GENERIC_QUERY_SUFFIXES):
            return False

    if has_generic_tokens and len(useful_tokens) <= 2:
        return False

    if len(useful_tokens) == 1 and len(useful_tokens[0]) < 4:
        return False

    return True


def result_matches_query(result: Dict[str, Any], query_text: str) -> bool:
    attrs = result.get("attrs", {})
    if not isinstance(attrs, dict):
        return False

    tokens = tokenize_query(query_text)

    if not tokens:
        return True

    searchable = " ".join(
        [
            strip_html(attrs.get("label")),
            strip_html(attrs.get("detail")),
            strip_html(attrs.get("name")),
        ]
    ).casefold()

    return any(token in searchable for token in tokens)


def build_title_fragments(title: str) -> List[str]:
    raw_title = str(title or "").strip()

    if not raw_title:
        return []

    split_patterns = [
        r"\s+-\s+",
        r"\s+–\s+",
        r"\s+—\s+",
        r":",
        r";",
        r"\(",
        r"\)",
        r"/",
        r",",
    ]

    fragments = [raw_title]

    for pattern in split_patterns:
        next_fragments = []
        for fragment in fragments:
            next_fragments.extend(re.split(pattern, fragment))
        fragments = next_fragments

    cleaned_fragments = []

    for fragment in fragments:
        fragment = normalize_query_text(fragment)
        if fragment:
            cleaned_fragments.append(fragment)

    return cleaned_fragments


def build_title_query_candidates(title: str) -> List[str]:
    normalized_title = normalize_query_text(title)

    if not normalized_title:
        return []

    candidates = []

    for fragment in build_title_fragments(title):
        if is_useful_query_candidate(fragment):
            candidates.append(fragment)

        for token in tokenize_query(fragment):
            if len(token) >= 4:
                candidates.append(token)

    cleaned_candidates = []
    seen = set()

    for candidate in candidates:
        candidate = trim_query_to_word_limit(candidate)

        if not is_useful_query_candidate(candidate):
            continue

        key = candidate.casefold()
        if key in seen:
            continue

        seen.add(key)
        cleaned_candidates.append(candidate)

    return cleaned_candidates[:MAX_QUERY_CANDIDATES]


def extract_named_text_candidates(
    text: Any,
    max_chars: int = MAX_TEXT_CHARS,
) -> List[str]:
    if text is None:
        return []

    window = str(text)[:max_chars]

    pattern = re.compile(
        r"\b(?:St\.\s+)?[A-ZÄÖÜ][a-zäöüéèà]+(?:[-\s][A-ZÄÖÜ][a-zäöüéèà]+){0,3}\b"
    )

    candidates = []

    for match in pattern.finditer(window):
        candidate = normalize_query_text(match.group(0))

        if not candidate:
            continue

        tokens = raw_tokens(candidate)

        if not tokens:
            continue

        useful_tokens = [
            token
            for token in tokens
            if token not in TEXT_CANDIDATE_EXCLUSION_TOKENS
        ]

        if not useful_tokens:
            continue

        if len(useful_tokens) == 1 and len(useful_tokens[0]) < 4:
            continue

        candidates.append(candidate)

    return candidates


def score_text_query_candidate(candidate: str) -> int:
    tokens = tokenize_query(candidate)
    score = 0

    if len(tokens) >= 2:
        score += 3

    if "-" in candidate:
        score += 2

    if candidate.startswith("St. "):
        score += 2

    if len(candidate) >= 8:
        score += 1

    return score


def build_text_query_candidates(
    clean_text: Any,
    max_candidates: int = MAX_TEXT_QUERY_CANDIDATES,
) -> List[str]:
    raw_candidates = extract_named_text_candidates(clean_text)

    counted: Dict[str, Dict[str, Any]] = {}

    for candidate in raw_candidates:
        normalized = normalize_query_text(candidate)

        if not is_useful_query_candidate(normalized):
            continue

        key = normalized.casefold()

        if key not in counted:
            counted[key] = {
                "candidate": normalized,
                "count": 0,
                "score": score_text_query_candidate(normalized),
            }

        counted[key]["count"] += 1

    ranked = sorted(
        counted.values(),
        key=lambda item: (
            -int(item["count"]),
            -int(item["score"]),
            str(item["candidate"]),
        ),
    )

    return [
        str(item["candidate"])
        for item in ranked[:max_candidates]
    ]


def parse_semicolon_values(value: Any) -> List[str]:
    if value is None:
        return []

    text = str(value).strip()

    if not text or text.casefold() == "nan":
        return []

    values = []

    for part in text.split(";"):
        part = normalize_query_text(part)
        if part:
            values.append(part)

    return values


def infer_canton_from_source_id(source_id: Any) -> str:
    text = str(source_id or "").casefold()

    canton_prefixes = {
        "ag_": "AG",
        "be_": "BE",
        "sg_": "SG",
        "zh_": "ZH",
    }

    for prefix, canton in canton_prefixes.items():
        if text.startswith(prefix):
            return canton

    return ""


def hint_matches_preferred_canton(
    hint: Dict[str, Any],
    preferred_canton: str,
) -> bool:
    if not preferred_canton:
        return False

    searchable = " ".join(
        [
            str(hint.get("name", "")),
            str(hint.get("detail", "")),
        ]
    ).casefold()

    return f"({preferred_canton.casefold()})" in searchable


def origin_priority(hint: Dict[str, Any]) -> int:
    origin = str(hint.get("origin", ""))

    if origin == "gg25":
        return 0

    if origin == "gazetteer":
        return 1

    return 5


def object_type_priority(hint: Dict[str, Any]) -> int:
    object_type = str(hint.get("object_type", ""))

    if object_type in PREFERRED_OBJECT_TYPE_PRIORITIES:
        return PREFERRED_OBJECT_TYPE_PRIORITIES[object_type]

    if object_type in LOW_PRIORITY_OBJECT_TYPES:
        return 99

    if not object_type:
        return 50

    return 20


def sort_geoadmin_hints(
    hints: List[Dict[str, Any]],
    preferred_canton: str = "",
) -> List[Dict[str, Any]]:
    return sorted(
        hints,
        key=lambda hint: (
            not hint_matches_preferred_canton(hint, preferred_canton),
            origin_priority(hint),
            object_type_priority(hint),
            int(hint.get("rank", 999)),
            str(hint.get("name", "")),
        ),
    )


def build_geoadmin_queries_for_lead(
    lead: Dict[str, Any],
    origins: str = DEFAULT_ORIGINS,
    limit: int = DEFAULT_LIMIT,
    sr: int = DEFAULT_SR,
) -> List[GeoAdminQuery]:
    candidates = []

    for municipality in parse_semicolon_values(lead.get("municipality_hints")):
        if is_useful_query_candidate(municipality):
            candidates.append(municipality)

    title = str(lead.get("title") or "")
    title_candidates = build_title_query_candidates(title)
    candidates.extend(title_candidates)

    if len(candidates) < 2:
        clean_text = lead.get("clean_text") or lead.get("text_preview") or ""
        candidates.extend(build_text_query_candidates(clean_text, max_candidates=2))

    cleaned_candidates = []
    seen = set()

    for candidate in candidates:
        candidate = trim_query_to_word_limit(candidate)

        if not is_useful_query_candidate(candidate):
            continue

        key = candidate.casefold()
        if key in seen:
            continue

        seen.add(key)
        cleaned_candidates.append(candidate)

    return [
        GeoAdminQuery(
            search_text=candidate,
            origins=origins,
            limit=limit,
            sr=sr,
        )
        for candidate in cleaned_candidates[:MAX_QUERY_CANDIDATES]
    ]


def load_cache(cache_path: Path) -> Dict[str, Dict[str, Any]]:
    if not cache_path.exists():
        return {}

    cache = {}

    with cache_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)
            cache_key = str(record.get("cache_key", ""))

            if cache_key:
                cache[cache_key] = record

    return cache


def append_cache_record(cache_path: Path, record: Dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with cache_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def fetch_geoadmin_response(
    query: GeoAdminQuery,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    response = requests.get(
        GEOADMIN_SEARCH_URL,
        params={
            "type": "locations",
            "searchText": query.search_text,
            "origins": query.origins,
            "limit": query.limit,
            "sr": query.sr,
        },
        timeout=timeout_seconds,
    )

    response.raise_for_status()
    return response.json()


def get_geoadmin_response_with_cache(
    query: GeoAdminQuery,
    cache_path: Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    cache = load_cache(cache_path)
    cache_key = query.cache_key()

    if cache_key in cache:
        cached = dict(cache[cache_key])
        cached["cache_hit"] = True
        return cached

    try:
        response_json = fetch_geoadmin_response(
            query=query,
            timeout_seconds=timeout_seconds,
        )

        record = {
            "cache_key": cache_key,
            "created_at": utc_now_iso(),
            "query": asdict(query),
            "ok": True,
            "error": None,
            "response": response_json,
        }

    except requests.RequestException as exc:
        record = {
            "cache_key": cache_key,
            "created_at": utc_now_iso(),
            "query": asdict(query),
            "ok": False,
            "error": str(exc),
            "response": None,
        }

    append_cache_record(cache_path, record)

    record["cache_hit"] = False
    return record


def parse_geoadmin_location_hints(
    cache_record: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not cache_record.get("ok"):
        return []

    response = cache_record.get("response") or {}
    results = response.get("results", [])

    if not isinstance(results, list):
        return []

    query = cache_record.get("query", {})
    search_text = query.get("search_text", "")

    hints = []
    seen = set()

    for rank, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            continue

        if not result_matches_query(result, search_text):
            continue

        attrs = result.get("attrs", {})
        if not isinstance(attrs, dict):
            attrs = {}

        raw_label = attrs.get("label") or attrs.get("detail") or attrs.get("name")
        label = strip_html(raw_label)
        object_type = extract_object_type_from_label(attrs.get("label"))
        origin = attrs.get("origin")
        x = attrs.get("x")
        y = attrs.get("y")
        detail = strip_html(attrs.get("detail"))

        if not label:
            continue

        dedupe_key = (
            label.casefold(),
            str(origin),
            str(x),
            str(y),
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)

        hints.append(
            {
                "hint_type": "geoadmin_location",
                "name": label,
                "object_type": object_type,
                "source": "geoadmin_search",
                "origin": origin,
                "query": search_text,
                "rank": rank,
                "x": x,
                "y": y,
                "detail": detail,
            }
        )

    return hints


def enrich_lead_with_geoadmin_hints(
    lead: Dict[str, Any],
    cache_path: Path,
    max_queries: int = 3,
) -> Dict[str, Any]:
    enriched = dict(lead)
    queries = build_geoadmin_queries_for_lead(enriched)[:max_queries]

    all_hints = []
    cache_hits = 0
    cache_misses = 0

    for query in queries:
        cache_record = get_geoadmin_response_with_cache(
            query=query,
            cache_path=cache_path,
        )

        if cache_record.get("cache_hit"):
            cache_hits += 1
        else:
            cache_misses += 1

        hints = parse_geoadmin_location_hints(cache_record)
        all_hints.extend(hints)

    preferred_canton = infer_canton_from_source_id(enriched.get("source_id"))
    sorted_hints = sort_geoadmin_hints(all_hints, preferred_canton)

    enriched["geoadmin_preferred_canton"] = preferred_canton
    enriched["geoadmin_location_hints"] = sorted_hints
    enriched["geoadmin_location_hint_count"] = len(sorted_hints)
    enriched["geoadmin_query_count"] = len(queries)
    enriched["geoadmin_cache_hits"] = cache_hits
    enriched["geoadmin_cache_misses"] = cache_misses

    return enriched