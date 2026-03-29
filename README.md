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

- `canton_id`
- `languages`
- `time_window_days`
- `source_registry`
- `source_policy`

### Source registry

`config/sources/<registry>.yaml` defines:

- `source_id`
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

Resolve configured sources and generate a snapshot:

`changescout --config-dir config --snapshot-dir artifacts`

This will:

- load the scope configuration
- load the source registry
- resolve active sources deterministically
- write a snapshot JSON file

## Output

A snapshot file is written to:

`artifacts/resolved_scope_snapshot.json`

It contains:

- scope configuration
- resolved active sources
- timestamp

This ensures reproducibility of each run.

## Project structure

- `src/changescout/` application code
- `config/` scope and source registry
- `tests/` automated tests
- `docs/` architecture and environment notes