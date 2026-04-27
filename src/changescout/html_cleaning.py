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


def extract_title(soup: BeautifulSoup) -> Optional[str]:
    meta = soup.find("meta", attrs={"name": "czhdev.title"})
    if meta and meta.get("content"):
        return meta["content"].strip()

    h1 = soup.select_one("h1.mdl-page-header__title")
    if h1:
        return h1.get_text(strip=True)

    h1_generic = soup.select_one("h1")
    if h1_generic:
        return h1_generic.get_text(strip=True)

    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        title = title.replace(" | Kanton Zürich", "")
        return title

    return None


def extract_main_text(soup: BeautifulSoup) -> Optional[str]:
    main = (
        soup.select_one("main#main")
        or soup.select_one("main")
        or soup.select_one("div#main")
        or soup.select_one("article")
    )

    if not main:
        return None

    for selector in [
        ".mdl-anchornav",
        ".mdl-feedback",
        ".mdl-contact",
        ".mdl-related-content",
        ".mdl-tag-group",
        ".mdl-page-header__breadcrumb",
        "nav",
        "footer",
        "script",
        "style",
    ]:
        for element in main.select(selector):
            element.decompose()

    text_blocks = []

    for element in main.select(".atm-lead"):
        text = element.get_text(separator=" ", strip=True)
        if text:
            text_blocks.append(text)

    rich_containers = main.select(".mdl-richtext, .mdl-accordion__panel-content")

    if rich_containers:
        for container in rich_containers:
            for element in container.select("h2, h3, h4, p, li"):
                text = element.get_text(separator=" ", strip=True)
                if text:
                    text_blocks.append(text)
    else:
        for element in main.select("h1, h2, h3, h4, p, li"):
            text = element.get_text(separator=" ", strip=True)
            if text:
                text_blocks.append(text)

    for element in main.select(".mdl-download_list__item .atm-linklist_item__text > span:first-child"):
        text = element.get_text(separator=" ", strip=True)
        if text:
            text_blocks.append(text)

    if not text_blocks:
        return None

    return "\n\n".join(text_blocks)


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    blocks = []
    seen = set()

    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue

        if re.search(r"\b(PDF|DOCX|XLSX|XLSM|ZIP|TIF)\b\s*\|", block):
            continue
        if re.search(r"\b\d+\s+Seiten\b", block):
            continue
        if re.search(r"\bDeutsch\b\s*\|", block):
            continue
        if re.fullmatch(r"Download", block, flags=re.IGNORECASE):
            continue

        if block.startswith("Download "):
            continue
        if block.startswith("Medienmitteilung vom"):
            continue
        if block.startswith("Regierungsratsbeschluss"):
            continue
        if block.startswith("Kantonsrätliche Motion"):
            continue
        if block.startswith("Infoveranstaltung"):
            continue
        if block.startswith("Visualisierung "):
            continue
        if block.startswith("Baustelleninfo vom"):
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