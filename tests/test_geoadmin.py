from pathlib import Path
from unittest.mock import Mock, patch

import requests

from changescout.geoadmin import (
    GeoAdminQuery,
    build_geoadmin_queries_for_lead,
    build_title_query_candidates,
    enrich_lead_with_geoadmin_hints,
    get_geoadmin_response_with_cache,
    infer_canton_from_source_id,
    parse_geoadmin_location_hints,
    result_matches_query,
    sort_geoadmin_hints,
    strip_html,
    tokenize_query,
    trim_query_to_word_limit,
)


def test_trim_query_to_word_limit() -> None:
    query = "one two three four five six seven eight nine ten eleven"

    result = trim_query_to_word_limit(query, max_words=10)

    assert result == "one two three four five six seven eight nine ten"


def test_build_title_query_candidates_splits_title_and_adds_specific_tokens() -> None:
    title = "VERAS – Verkehrsinfrastruktur Entwicklung Raum Suhr"

    result = build_title_query_candidates(title)

    assert "VERAS" in result
    assert "suhr" in result
    assert "VERAS Verkehrsinfrastruktur Entwicklung Raum Suhr" not in result


def test_build_title_query_candidates_extracts_specific_name_from_generic_title() -> None:
    title = "SBB-Unterführung Buriet"

    result = build_title_query_candidates(title)

    assert result == ["buriet"]


def test_build_geoadmin_queries_for_lead() -> None:
    lead = {
        "title": "SBB-Unterführung Buriet",
    }

    queries = build_geoadmin_queries_for_lead(lead)

    assert queries
    assert queries[0].search_text == "buriet"
    assert queries[0].origins == "gazetteer,gg25"


def test_build_geoadmin_queries_prefers_local_municipality_hints() -> None:
    lead = {
        "title": "Buchs – Sanierung und Aufwertung der Ortsdurchfahrt",
        "municipality_hints": "Buchs",
    }

    queries = build_geoadmin_queries_for_lead(lead)

    assert queries[0].search_text == "Buchs"


def test_strip_html_removes_markup() -> None:
    result = strip_html("<i>Ort</i> <b>Suhr</b> (AG) - Suhr")

    assert result == "Ort Suhr (AG) - Suhr"


def test_tokenize_query_removes_generic_tokens() -> None:
    result = tokenize_query("SBB-Unterführung Buriet")

    assert result == ["buriet"]


def test_result_matches_query_rejects_unrelated_broad_result() -> None:
    result = {
        "attrs": {
            "label": "<i>Grossregion</i> <b>Jura</b>",
            "detail": "jura loveresse biel bienne",
        }
    }

    assert result_matches_query(result, "SBB-Unterführung Buriet") is False


def test_result_matches_query_accepts_specific_result() -> None:
    result = {
        "attrs": {
            "label": "<i>Quartierteil</i> <b>Buriet</b> (SG) - Thal",
            "detail": "buriet thal",
        }
    }

    assert result_matches_query(result, "SBB-Unterführung Buriet") is True


def test_infer_canton_from_source_id() -> None:
    assert infer_canton_from_source_id("ag_strassenprojekte") == "AG"
    assert infer_canton_from_source_id("sg_tiefbau") == "SG"
    assert infer_canton_from_source_id("unknown") == ""


def test_sort_geoadmin_hints_prefers_source_canton() -> None:
    hints = [
        {
            "name": "Buchs (ZH)",
            "detail": "buchs zh",
            "rank": 1,
        },
        {
            "name": "Buchs (AG)",
            "detail": "buchs ag",
            "rank": 2,
        },
    ]

    result = sort_geoadmin_hints(hints, preferred_canton="AG")

    assert result[0]["name"] == "Buchs (AG)"


def test_parse_geoadmin_location_hints() -> None:
    cache_record = {
        "ok": True,
        "query": {
            "search_text": "Buriet",
        },
        "response": {
            "results": [
                {
                    "attrs": {
                        "label": "Buriet <b>Thal</b>",
                        "origin": "gazetteer",
                        "x": 2760000,
                        "y": 1260000,
                        "detail": "buriet thal",
                    }
                }
            ]
        },
    }

    hints = parse_geoadmin_location_hints(cache_record)

    assert len(hints) == 1
    assert hints[0]["hint_type"] == "geoadmin_location"
    assert hints[0]["name"] == "Buriet Thal"
    assert hints[0]["query"] == "Buriet"
    assert hints[0]["origin"] == "gazetteer"
    assert hints[0]["x"] == 2760000
    assert hints[0]["y"] == 1260000
    assert hints[0]["detail"] == "buriet thal"


def test_parse_geoadmin_location_hints_filters_unrelated_results() -> None:
    cache_record = {
        "ok": True,
        "query": {
            "search_text": "SBB-Unterführung Buriet",
        },
        "response": {
            "results": [
                {
                    "attrs": {
                        "label": "<i>Grossregion</i> <b>Jura</b>",
                        "origin": "gazetteer",
                        "x": 2600000,
                        "y": 1200000,
                        "detail": "jura loveresse biel bienne",
                    }
                },
                {
                    "attrs": {
                        "label": "<i>Quartierteil</i> <b>Buriet</b> (SG) - Thal",
                        "origin": "gazetteer",
                        "x": 2760000,
                        "y": 1260000,
                        "detail": "buriet thal",
                    }
                },
            ]
        },
    }

    hints = parse_geoadmin_location_hints(cache_record)

    assert len(hints) == 1
    assert hints[0]["name"] == "Quartierteil Buriet (SG) - Thal"


def test_parse_geoadmin_location_hints_deduplicates_results() -> None:
    cache_record = {
        "ok": True,
        "query": {
            "search_text": "Neeracherried",
        },
        "response": {
            "results": [
                {
                    "attrs": {
                        "label": "<i>Turm</i> <b>Beobachtungsturm Neeracherried</b> (ZH) - Höri",
                        "origin": "gazetteer",
                        "x": 2679184.25,
                        "y": 1262147.125,
                        "detail": "beobachtungsturm neeracherried hoeri",
                    }
                },
                {
                    "attrs": {
                        "label": "<i>Turm</i> <b>Beobachtungsturm Neeracherried</b> (ZH) - Höri",
                        "origin": "gazetteer",
                        "x": 2679184.25,
                        "y": 1262147.125,
                        "detail": "beobachtungsturm neeracherried hoeri",
                    }
                },
            ]
        },
    }

    hints = parse_geoadmin_location_hints(cache_record)

    assert len(hints) == 1


def test_get_geoadmin_response_with_cache_writes_and_reuses_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.jsonl"
    query = GeoAdminQuery(search_text="Suhr")

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"results": []}

    with patch("changescout.geoadmin.requests.get", return_value=mock_response) as mock_get:
        first = get_geoadmin_response_with_cache(query, cache_path)
        second = get_geoadmin_response_with_cache(query, cache_path)

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert mock_get.call_count == 1
    assert cache_path.exists()


def test_get_geoadmin_response_with_cache_handles_request_failure(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.jsonl"
    query = GeoAdminQuery(search_text="Suhr")

    with patch(
        "changescout.geoadmin.requests.get",
        side_effect=requests.Timeout("timeout"),
    ):
        result = get_geoadmin_response_with_cache(query, cache_path)

    assert result["ok"] is False
    assert result["cache_hit"] is False
    assert "timeout" in result["error"]


def test_enrich_lead_with_geoadmin_hints(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.jsonl"
    lead = {
        "title": "Buriet",
        "source_id": "sg_tiefbau",
    }

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "results": [
            {
                "attrs": {
                    "label": "Buriet",
                    "origin": "gazetteer",
                    "x": 2760000,
                    "y": 1260000,
                    "detail": "buriet thal",
                }
            }
        ]
    }

    with patch("changescout.geoadmin.requests.get", return_value=mock_response):
        enriched = enrich_lead_with_geoadmin_hints(
            lead=lead,
            cache_path=cache_path,
            max_queries=1,
        )

    assert enriched["geoadmin_preferred_canton"] == "SG"
    assert enriched["geoadmin_location_hint_count"] == 1
    assert enriched["geoadmin_query_count"] == 1
    assert enriched["geoadmin_cache_hits"] == 0
    assert enriched["geoadmin_cache_misses"] == 1
    assert enriched["geoadmin_location_hints"][0]["name"] == "Buriet"