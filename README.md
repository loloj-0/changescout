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

## Current limitations

Discovery currently does not:

- fetch discovered project pages
- extract page content
- score relevance
- classify change types
- track known URLs across runs
- confirm whether a discovered page reflects a finished real world change

## Project structure

- `src/changescout/` application code
- `config/` scope and source registry
- `tests/` automated tests
- `docs/` architecture and environment notes
- `artifacts/` generated snapshots and discovery outputs