import json
from pathlib import Path

INPUT_FILES = [
    "artifacts/scored_be_unique_final.jsonl",
    "artifacts/scored_ag_unique_final.jsonl",
    "artifacts/scored_sg_unique_final.jsonl",
]

OUTPUT_PATH = "data/annotation/candidates/all_candidates.jsonl"


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main():
    all_records = []
    seen_urls = set()

    for path in INPUT_FILES:
        records = load(path)

        for r in records:
            url = r["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            all_records.append(r)

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("total:", len(all_records))


if __name__ == "__main__":
    main()