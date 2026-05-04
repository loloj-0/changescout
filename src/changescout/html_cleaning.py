from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Tuple
from langdetect import detect, LangDetectException
import json
import re


def load_html(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def is_invalid_title(title: Optional[str]) -> bool:
    if not title:
        return True

    normalized = " ".join(title.split()).strip().lower()

    invalid_titles = {
        "javascript deaktiviert oder nicht unterstützt.",
        "javascript deaktiviert oder nicht unterstützt",
        "navigation",
        "hauptnavigation",
        "bereichsnavigation",
        "unternavigation",
        "suche",
        "kontakt",
        "sitemap",
    }

    return normalized in invalid_titles


def clean_html_title(title: str) -> str:
    title = title.strip()

    suffixes = [
        " | Kanton Zürich",
        " - Kanton Aargau",
        " | sg.ch",
        " | Kanton St.Gallen",
        " | Kanton Bern",
        " | Kanton Graubünden",
        " - Kanton Graubünden",
    ]

    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()

    return title


def extract_title(soup: BeautifulSoup) -> Optional[str]:
    candidates = []

    meta_selectors = [
        {"name": "czhdev.title"},
        {"property": "og:title"},
        {"name": "title"},
    ]

    for attrs in meta_selectors:
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            candidates.append(meta["content"].strip())

    if soup.title and soup.title.string:
        candidates.append(clean_html_title(soup.title.string))

    for selector in [
        "h1.mdl-page-header__title",
        "main h1",
        "article h1",
        ".ms-rtestate-field h1",
        ".article-content h1",
        ".entry-content h1",
        ".page-content h1",
        ".body-content h1",
    ]:
        h1 = soup.select_one(selector)
        if h1:
            candidates.append(h1.get_text(separator=" ", strip=True))

    for selector in [
        "#DeltaPlaceHolderMain h1",
        "#contentBox h1",
        "h1",
    ]:
        h1 = soup.select_one(selector)
        if h1:
            candidates.append(h1.get_text(separator=" ", strip=True))

    for candidate in candidates:
        if not is_invalid_title(candidate):
            return candidate

    return None


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_boilerplate_elements(container: BeautifulSoup) -> None:
    selectors = [
        ".mdl-anchornav",
        ".mdl-feedback",
        ".mdl-contact",
        ".mdl-related-content",
        ".mdl-tag-group",
        ".mdl-page-header__breadcrumb",
        ".breadcrumb",
        ".breadcrumbs",
        ".footer",
        ".site-footer",
        ".social",
        ".social-media",
        ".share",
        ".sharing",
        ".skip",
        ".skiplink",
        ".skiplinks",
        "#sideNavBox",
        "#suiteBar",
        "#s4-ribbonrow",
        "#s4-titlerow",
        "#DeltaPageStatusBar",
        ".ms-core-navigation",
        ".ms-breadcrumb-box",
        ".ms-webpart-chrome-title",
        "nav",
        "footer",
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
    ]

    for selector in selectors:
        for element in container.select(selector):
            element.decompose()


def find_main_container(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    selectors = [
        "main#main",
        "main",
        "div#main",
        "article",
        "[role='main']",
        "#DeltaPlaceHolderMain",
        "#contentBox",
        "#ctl00_PlaceHolderMain",
        ".ms-rtestate-field",
        ".content",
        ".main-content",
        ".page-content",
        ".article-content",
        ".entry-content",
        ".body-content",
        ".mdl-richtext",
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return element

    return soup.body


def extract_text_blocks_from_container(container: BeautifulSoup) -> List[str]:
    text_blocks: List[str] = []

    for element in container.select(".atm-lead"):
        text = element.get_text(separator=" ", strip=True)
        if text:
            text_blocks.append(text)

    rich_containers = container.select(
        ".mdl-richtext, "
        ".mdl-accordion__panel-content, "
        ".ms-rtestate-field, "
        ".article-content, "
        ".entry-content, "
        ".page-content, "
        ".body-content"
    )

    if rich_containers:
        for rich_container in rich_containers:
            for element in rich_container.select("h1, h2, h3, h4, p, li"):
                text = element.get_text(separator=" ", strip=True)
                if text:
                    text_blocks.append(text)
    else:
        for element in container.select("h1, h2, h3, h4, p, li"):
            text = element.get_text(separator=" ", strip=True)
            if text:
                text_blocks.append(text)

    for element in container.select(".mdl-download_list__item .atm-linklist_item__text > span:first-child"):
        text = element.get_text(separator=" ", strip=True)
        if text:
            text_blocks.append(text)

    if not text_blocks:
        fallback_text = container.get_text(separator=" ", strip=True)
        fallback_text = " ".join(fallback_text.split())
        if fallback_text:
            text_blocks.append(fallback_text)

    return text_blocks


def extract_main_text(soup: BeautifulSoup) -> Optional[str]:
    main = find_main_container(soup)

    if not main:
        return None

    remove_boilerplate_elements(main)

    text_blocks = extract_text_blocks_from_container(main)

    if not text_blocks:
        return None

    return "\n\n".join(text_blocks)


def is_noise_block(block: str) -> bool:
    normalized = " ".join(block.split()).strip()
    lower = normalized.lower()

    if not normalized:
        return True

    if re.search(r"\b(PDF|DOCX|XLSX|XLSM|ZIP|TIF)\b\s*\|", normalized):
        return True

    if re.search(r"\b\d+\s+Seiten\b", normalized):
        return True

    if re.search(r"\bDeutsch\b\s*\|", normalized):
        return True

    if re.fullmatch(r"Download", normalized, flags=re.IGNORECASE):
        return True

    exact_noise = {
        "navigation",
        "suche",
        "kontakt",
        "sitemap",
        "stellen",
        "impressum",
        "facebook",
        "x",
        "mail",
        "whatsapp",
        "alle webseiten",
        "kanton graubünden",
        "kanton graubuenden",
        "springe zum seiteninhalt",
        "springe zur navigation",
        "unternavigation öffnen",
        "unternavigation oeffnen",
        "hauptnavigation",
        "bereichsnavigation",
        "sprachwahl",
        "deutsch",
        "rumantsch",
        "italiano",
    }

    if lower in exact_noise:
        return True

    startswith_noise = [
        "Download ",
        "Medienmitteilung vom",
        "Regierungsratsbeschluss",
        "Kantonsrätliche Motion",
        "Infoveranstaltung",
        "Visualisierung ",
        "Baustelleninfo vom",
        "© ",
    ]

    for prefix in startswith_noise:
        if normalized.startswith(prefix):
            return True

    if len(normalized) <= 2:
        return True

    return False


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None

    text = normalize_text(text)

    blocks = []
    seen = set()

    for block in text.split("\n\n"):
        block = normalize_text(block)
        if is_noise_block(block):
            continue

        if block in seen:
            continue

        seen.add(block)
        blocks.append(block)

    if not blocks:
        return None

    return "\n\n".join(blocks)


def detect_language(text: Optional[str]) -> str:
    if not text:
        return "unknown"

    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def is_technical_navigation_url(url: Optional[str]) -> bool:
    if not url:
        return False

    normalized = url.lower()

    technical_fragments = [
        "skip.aspx",
    ]

    return any(fragment in normalized for fragment in technical_fragments)


def load_crawl_records(path: str) -> List[Dict[str, Any]]:
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    return records


def write_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_normalized_document(
    crawl_record: Dict[str, Any],
    title: Optional[str],
    clean_text_value: str,
    language: str,
) -> Dict[str, Any]:
    return {
        "document_id": crawl_record["content_hash"],
        "source_id": crawl_record["source_id"],
        "url": crawl_record["url"],
        "title": title,
        "clean_text": clean_text_value,
        "language": language,
        "crawl_timestamp": crawl_record["fetched_at"],
        "html_path": crawl_record["html_path"],
        "clean_text_length": len(clean_text_value),
    }


def build_exclusion_record(
    crawl_record: Dict[str, Any],
    reason: str,
    title: Optional[str],
    language: str,
    raw_length: int,
    clean_length: int,
) -> Dict[str, Any]:
    return {
        "document_id": crawl_record.get("content_hash"),
        "source_id": crawl_record["source_id"],
        "url": crawl_record["url"],
        "title": title,
        "reason": reason,
        "language": language,
        "raw_length": raw_length,
        "clean_length": clean_length,
        "crawl_timestamp": crawl_record["fetched_at"],
        "html_path": crawl_record.get("html_path"),
    }


def process_document(
    crawl_record: Dict[str, Any],
    min_text_length: int = 300,
    allowed_languages: Optional[List[str]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if allowed_languages is None:
        allowed_languages = ["de"]

    if crawl_record.get("status_code") != 200:
        exclusion = build_exclusion_record(
            crawl_record=crawl_record,
            reason="crawl_failed",
            title=None,
            language="unknown",
            raw_length=0,
            clean_length=0,
        )
        return None, exclusion

    if is_technical_navigation_url(crawl_record.get("url")):
        exclusion = build_exclusion_record(
            crawl_record=crawl_record,
            reason="technical_navigation_url",
            title=None,
            language="unknown",
            raw_length=0,
            clean_length=0,
        )
        return None, exclusion

    html_path = crawl_record.get("html_path")
    if not html_path:
        exclusion = build_exclusion_record(
            crawl_record=crawl_record,
            reason="missing_html_path",
            title=None,
            language="unknown",
            raw_length=0,
            clean_length=0,
        )
        return None, exclusion

    try:
        html = load_html(html_path)
        raw_length = len(html)
        soup = parse_html(html)

        title = extract_title(soup)
        main_text = extract_main_text(soup)

        if main_text is None:
            exclusion = build_exclusion_record(
                crawl_record=crawl_record,
                reason="no_main_text",
                title=title,
                language="unknown",
                raw_length=raw_length,
                clean_length=0,
            )
            return None, exclusion

        cleaned = clean_text(main_text)
        clean_length = len(cleaned) if cleaned else 0

        if not cleaned:
            exclusion = build_exclusion_record(
                crawl_record=crawl_record,
                reason="extraction_failed",
                title=title,
                language="unknown",
                raw_length=raw_length,
                clean_length=0,
            )
            return None, exclusion

        if clean_length < min_text_length:
            language = detect_language(cleaned)
            exclusion = build_exclusion_record(
                crawl_record=crawl_record,
                reason="too_short",
                title=title,
                language=language,
                raw_length=raw_length,
                clean_length=clean_length,
            )
            return None, exclusion

        language = detect_language(cleaned)

        if language not in allowed_languages:
            exclusion = build_exclusion_record(
                crawl_record=crawl_record,
                reason="unsupported_language",
                title=title,
                language=language,
                raw_length=raw_length,
                clean_length=clean_length,
            )
            return None, exclusion

        document = build_normalized_document(
            crawl_record=crawl_record,
            title=title,
            clean_text_value=cleaned,
            language=language,
        )
        return document, None

    except Exception:
        exclusion = build_exclusion_record(
            crawl_record=crawl_record,
            reason="extraction_failed",
            title=None,
            language="unknown",
            raw_length=0,
            clean_length=0,
        )
        return None, exclusion


def process_crawl_records(
    input_path: str,
    cleaned_output_path: str,
    excluded_output_path: str,
    report_output_path: str,
    min_text_length: int = 300,
    allowed_languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if allowed_languages is None:
        allowed_languages = ["de"]

    crawl_records = load_crawl_records(input_path)

    cleaned_records = []
    excluded_records = []

    for crawl_record in crawl_records:
        cleaned, excluded = process_document(
            crawl_record=crawl_record,
            min_text_length=min_text_length,
            allowed_languages=allowed_languages,
        )

        if cleaned is not None:
            cleaned_records.append(cleaned)

        if excluded is not None:
            excluded_records.append(excluded)

    exclusion_counts: Dict[str, int] = {}
    for record in excluded_records:
        reason = record["reason"]
        exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1

    avg_text_length = 0.0
    if cleaned_records:
        avg_text_length = sum(r["clean_text_length"] for r in cleaned_records) / len(cleaned_records)

    report = {
        "total_documents": len(crawl_records),
        "included_documents": len(cleaned_records),
        "excluded_documents": len(excluded_records),
        "inclusion_rate": len(cleaned_records) / len(crawl_records) if crawl_records else 0.0,
        "avg_clean_text_length": avg_text_length,
        "exclusion_reasons": exclusion_counts,
    }

    write_jsonl(cleaned_output_path, cleaned_records)
    write_jsonl(excluded_output_path, excluded_records)
    write_json(report_output_path, report)

    return report


if __name__ == "__main__":
    report = process_crawl_records(
        input_path="artifacts/crawl.jsonl",
        cleaned_output_path="artifacts/cleaned.jsonl",
        excluded_output_path="artifacts/excluded.jsonl",
        report_output_path="artifacts/html_cleaning_report.json",
        min_text_length=300,
        allowed_languages=["de"],
    )

    print("HTML cleaning completed")
    print(json.dumps(report, ensure_ascii=False, indent=2))