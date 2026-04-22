# ChangeScout

ChangeScout is a deterministic monitoring pipeline for canton scoped observation of official web sources.

## Initial MVP goal

The first MVP generates deterministic leads for potential TLM relevant real world changes within one canton.

The system resolves the same active source set from the same config and produces reproducible candidate leads from manually curated official canton level sources.

The MVP does not try to automatically confirm whether a lead already corresponds to a finished or visible geometry change.
Manual validation remains part of the workflow.

## Current MVP source model

The MVP supports manually curated official source definitions in a versioned registry.

A source can currently be defined as:

- `html_list` for a concrete list page
- `html_pattern` for a section root plus URL include patterns used to discover relevant subpages

This allows the MVP to monitor official infrastructure project sections even when no clean central list page is available.

## Configuration

Monitoring is controlled entirely via configuration.

### Scope

`config/scope.yaml` defines:

- `version`
- `canton_id`
- `languages`
- `time_window_days`
- `source_registry`
- `source_policy`

### Source registry

`config/sources/<registry>.yaml` defines:

- `source_id`
- `name`
- `base_url`
- `crawl_type`
- `include_patterns` for `html_pattern`
- `crawl_frequency_hours`
- `active`

The value of `source_registry` in `config/scope.yaml` maps directly to the registry file name.

Example:

- `source_registry: "zh"` maps to `config/sources/zh.yaml`

Only sources defined in that file are used by the pipeline.

## Usage

### Environment setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Resolve configured sources and generate a snapshot

```bash
PYTHONPATH=src python -m changescout.cli snapshot --config-dir config --snapshot-dir artifacts
```

This will:

- load the scope configuration
- load the source registry
- resolve active sources deterministically
- write a snapshot JSON file

### Run discovery

```bash
PYTHONPATH=src python -m changescout.cli discover --config-dir config --output artifacts/discovery.jsonl
```

This will:

- load the scope configuration
- load the source registry
- resolve active sources deterministically
- fetch configured discovery entry pages
- extract and normalize links
- filter discovered URLs by configured include patterns
- exclude common non HTML asset URLs such as PDF, image, Office, and ZIP files
- deduplicate discovered URLs per source
- write discovered candidate URLs as JSONL

### Run crawling

```bash
PYTHONPATH=src python -m changescout.cli crawl --input artifacts/discovery.jsonl --output artifacts/crawl.jsonl --html-base-dir data/crawling --run-id run_001
```

This will:

- load discovered URLs from JSONL
- fetch each URL via HTTP
- compute a deterministic content hash
- store raw HTML to disk
- create structured crawl records
- log success and failure per URL
- continue processing on failures
- write crawl output as JSONL

## Output

### Snapshot output

A snapshot file is written to:

`artifacts/resolved_scope_snapshot.json`

It contains:

- scope configuration
- resolved active sources
- timestamp

This ensures reproducibility of each run.

### Discovery output

A discovery output file is written to the path provided with `--output`.

Example:

`artifacts/discovery.jsonl`

It contains one JSON record per discovered candidate URL.

Each record contains at least:

- `source_id`
- `url`
- `discovered_at`

Optional traceability fields may include:

- `base_url`
- `matched_pattern`

Example record:

```json
{
  "source_id": "zh_baustellen",
  "url": "https://www.zh.ch/de/planen-bauen/tiefbau/baustellen/strassenprojekt-buelach-glattfelden.html",
  "discovered_at": "2026-03-29T15:03:14.538354+00:00",
  "base_url": "https://www.zh.ch/de/planen-bauen/tiefbau/baustellen.html",
  "matched_pattern": "/baustellen/strassenprojekt-"
}
```

### Crawl output

A crawl output file is written to the path provided with `--output`.

Example:

`artifacts/crawl.jsonl`

It contains one JSON record per fetched page.

Each record contains:

- `source_id`
- `url`
- `fetched_at`
- `status_code`
- `content_hash` for successful fetches
- `html_path` for successful fetches
- `error` for failed fetches
- `discovered_at`

Example success record:

```json
{
  "source_id": "zh_tiefbau",
  "url": "https://example.org",
  "fetched_at": "2026-04-22T14:55:26.313449+00:00",
  "status_code": 200,
  "content_hash": "fb91d75a6bb430787a61b0aec5e374f580030f2878e1613eab5ca6310f7bbb9a",
  "html_path": "data/crawling/run_001/zh_tiefbau/fb91d75a6bb430787a61b0aec5e374f580030f2878e1613eab5ca6310f7bbb9a.html",
  "error": null,
  "discovered_at": "2026-04-22T10:00:00Z"
}
```

Example failure record:

```json
{
  "source_id": "zh_tiefbau",
  "url": "https://does-not-exist.invalid",
  "fetched_at": "2026-04-22T14:55:26.338081+00:00",
  "status_code": 0,
  "content_hash": null,
  "html_path": null,
  "error": "timeout",
  "discovered_at": "2026-04-22T10:05:00Z"
}
```

### HTML storage

Raw HTML files are stored under:

`data/crawling/<run_id>/<source_id>/<content_hash>.html`

This layout ensures:

- deterministic storage paths
- no collisions across runs
- reproducible mapping between records and stored content

## Current discovery behavior

Discovery currently:

- fetches source HTML
- extracts anchor links
- normalizes links to absolute URLs
- filters by configured include patterns
- excludes common non HTML asset URLs such as PDF, image, Office, and ZIP files
- deduplicates discovered URLs per source and run
- writes final discovery records to JSONL
- logs source level discovery progress and failures

## Current crawling behavior

Crawling currently:

- fetches discovered URLs via HTTP GET
- stores raw HTML for all successful HTTP responses
- computes a deterministic SHA256 content hash
- writes HTML files to a run scoped directory structure
- creates structured crawl records for each URL
- logs success and failure per URL
- continues processing on failures
- writes crawl output as JSONL

## Current limitations

Discovery currently does not:

- fetch discovered project pages
- extract page content
- score relevance
- classify change types
- track known URLs across runs
- confirm whether a discovered page reflects a finished real world change

Crawling currently does not:

- interpret HTML content
- extract structured information from pages
- deduplicate pages across runs
- retry failed requests
- normalize HTML content before hashing

## Project structure

- `src/changescout/` application code
- `config/` scope and source registry
- `tests/` automated tests
- `docs/` architecture and environment notes
- `artifacts/` generated snapshots, discovery outputs, and crawl outputs
- `data/crawling/` stored raw HTML files