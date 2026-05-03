from pathlib import Path
from unittest.mock import Mock, patch

import requests

from changescout.geoadmin import (
    GeoAdminQuery,
    build_geoadmin_queries_for_lead,
    build_text_query_candidates,
    build_title_query_candidates,
    enrich_lead_with_geoadmin_hints,
    extract_named_text_candidates,
    extract_object_type_from_label,
    get_geoadmin_response_with_cache,
    infer_canton_from_source_id,
    object_type_priority,
    origin_priority,
    parse_geoadmin_location_hints,
    result_matches_query,
    select_best_geoadmin_location,
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


def test_extract_named_text_candidates_from_clean_text() -> None:
    text = (
        "Das Projekt betrifft die Rosenbergsau bis Binnenkanal. "
        "Weitere Arbeiten erfolgen in St. Gallen und Möriken-Wildegg."
    )

    result = extract_named_text_candidates(text)

    assert "Rosenbergsau" in result
    assert "Binnenkanal" in result
    assert "St. Gallen" in result
    assert "Möriken-Wildegg" in result


def test_build_text_query_candidates_filters_generic_words() -> None:
    text = (
        "Publiziert 24.03.26 Drucken. "
        "Das Projekt Sanierung betrifft die Gemeinde Suhr und den Raum Langelen."
    )

    result = build_text_query_candidates(text)

    assert "Publiziert" not in result
    assert "Drucken" not in result
    assert "Sanierung" not in result
    assert any("Suhr" in candidate or "Langelen" in candidate for candidate in result)


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


def test_build_geoadmin_queries_uses_clean_text_as_fallback() -> None:
    lead = {
        "title": "Öffentliche Planauflage",
        "clean_text": "Das Vorhaben betrifft Rosenbergsau bis Binnenkanal.",
    }

    queries = build_geoadmin_queries_for_lead(lead)

    search_texts = [query.search_text for query in queries]

    assert "Rosenbergsau" in search_texts or "Binnenkanal" in search_texts


def test_strip_html_removes_markup() -> None:
    result = strip_html("<i>Ort</i> <b>Suhr</b> (AG) - Suhr")

    assert result == "Ort Suhr (AG) - Suhr"


def test_extract_object_type_from_label() -> None:
    label = "<i>Quartierteil</i> <b>Buriet</b> (SG) - Thal"

    result = extract_object_type_from_label(label)

    assert result == "Quartierteil"


def test_extract_object_type_from_label_returns_empty_without_type() -> None:
    result = extract_object_type_from_label("Buriet")

    assert result == ""


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


def test_origin_priority_prefers_gg25_over_gazetteer() -> None:
    assert origin_priority({"origin": "gg25"}) < origin_priority({"origin": "gazetteer"})


def test_object_type_priority_prefers_place_over_grossregion() -> None:
    place = {
        "object_type": "Ort",
    }
    grossregion = {
        "object_type": "Grossregion",
    }

    assert object_type_priority(place) < object_type_priority(grossregion)


def test_sort_geoadmin_hints_prefers_source_canton() -> None:
    hints = [
        {
            "name": "Buchs (ZH)",
            "detail": "buchs zh",
            "object_type": "",
            "origin": "gg25",
            "rank": 1,
        },
        {
            "name": "Buchs (AG)",
            "detail": "buchs ag",
            "object_type": "",
            "origin": "gg25",
            "rank": 2,
        },
    ]

    result = sort_geoadmin_hints(hints, preferred_canton="AG")

    assert result[0]["name"] == "Buchs (AG)"


def test_sort_geoadmin_hints_prefers_better_object_type() -> None:
    hints = [
        {
            "name": "Mittelland",
            "detail": "mittelland",
            "object_type": "Grossregion",
            "origin": "gazetteer",
            "rank": 1,
        },
        {
            "name": "Stettlen (BE)",
            "detail": "stettlen be",
            "object_type": "Ort",
            "origin": "gazetteer",
            "rank": 2,
        },
    ]

    result = sort_geoadmin_hints(hints, preferred_canton="BE")

    assert result[0]["name"] == "Stettlen (BE)"


def test_select_best_geoadmin_location_returns_first_hint_with_coordinates() -> None:
    hints = [
        {
            "name": "No coordinate",
            "x": None,
            "y": None,
        },
        {
            "name": "Suhr (AG)",
            "x": 2648331.25,
            "y": 1247502.625,
            "origin": "gg25",
        },
    ]

    result = select_best_geoadmin_location(hints)

    assert result["name"] == "Suhr (AG)"


def test_select_best_geoadmin_location_returns_empty_when_no_coordinates() -> None:
    hints = [
        {
            "name": "No coordinate",
            "x": None,
            "y": None,
        }
    ]

    result = select_best_geoadmin_location(hints)

    assert result == {}


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
    assert hints[0]["object_type"] == ""
    assert hints[0]["query"] == "Buriet"
    assert hints[0]["origin"] == "gazetteer"
    assert hints[0]["x"] == 2760000
    assert hints[0]["y"] == 1260000
    assert hints[0]["detail"] == "buriet thal"


def test_parse_geoadmin_location_hints_extracts_object_type() -> None:
    cache_record = {
        "ok": True,
        "query": {
            "search_text": "Buriet",
        },
        "response": {
            "results": [
                {
                    "attrs": {
                        "label": "<i>Quartierteil</i> <b>Buriet</b> (SG) - Thal",
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
    assert hints[0]["object_type"] == "Quartierteil"


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
    assert hints[0]["object_type"] == "Quartierteil"


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
    assert enriched["geoadmin_best_location_name"] == "Buriet"
    assert enriched["geoadmin_best_location_x"] == 2760000
    assert enriched["geoadmin_best_location_y"] == 1260000
    assert enriched["geoadmin_best_location_origin"] == "gazetteer"