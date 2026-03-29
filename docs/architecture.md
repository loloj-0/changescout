# Architecture

## MVP Scope Decision

The MVP monitoring scope is limited to a single canton.

### Selected canton
Zürich

### Scope policy
The system monitors only manually curated official canton level web sources for the selected canton.

The purpose of monitoring is not to directly confirm finished real world changes.
The purpose is to generate deterministic leads for potential TLM relevant changes that can be prioritized for manual validation.

### Included in MVP
- one canton only
- manual source curation
- official canton level web sources
- project and publication pages that may indicate planned, ongoing, or completed infrastructure changes
- versioned scope configuration in Git
- deterministic source selection from config
- deterministic lead generation from configured sources

### Explicitly excluded from MVP
- municipalities
- unofficial media sources
- associations and private organizations
- social media channels
- automatic source discovery
- cross canton support in runtime behavior
- automatic confirmation that a detected lead corresponds to a finished TLM relevant change

### Rationale
The MVP prioritizes determinism, reviewability, and low operational complexity.

A narrow and explicit source boundary is required so that the same configuration always resolves to the same source set.

For TLM relevant changes, official project and infrastructure pages are often more useful than generic news pages because they provide earlier and more persistent signals about possible future geometry changes.

The MVP therefore focuses on lead generation instead of final change confirmation.
This allows earlier awareness of potentially relevant real world developments, while keeping manual review in the loop.

### Extensibility
The configuration model must be designed so that additional cantons can be added later without changing the core logic.

This means canton specific scope and source registries are data driven, not hardcoded.

## Configuration Model

The monitoring configuration is separated into scope definition and source registry.

### Scope definition

The file `config/scope.yaml` defines the active monitoring context for a run.

Current fields:
- `version`: integer representing the schema version of the scope configuration
- `canton_id`: selected canton identifier
- `languages`: allowed language set for the monitoring scope
- `time_window_days`: defines the temporal lookback window applied during data collection and filtering steps
- `source_registry`: name of the source registry file to load
- `source_policy`: policy label describing which source types are intended to be allowed

This file defines the scope of monitoring, but not the concrete source endpoints.

### Source registry

The file `config/sources/<registry>.yaml` defines the concrete source entries for the selected registry.

The source registry is the single explicit source of truth for which official sources belong to the monitored source set.

It defines the concrete source endpoints and discovery rules that are allowed for the active monitoring scope.

Only sources explicitly listed in the versioned source registry may be used by the pipeline.

Each source entry contains:
- `source_id`
- `name`
- `base_url`
- `crawl_type`
- `crawl_frequency_hours`
- `active`
- optional `include_patterns` for pattern based discovery sources

For `html_pattern` sources, `include_patterns` is required and defines which discovered URLs belong to the monitored source surface.

This file defines which exact source endpoints belong to the monitored source set.

### Source inclusion rule

A source is included in the monitoring scope only if it is explicitly defined in the versioned source registry.

For the MVP, the `source_policy` field is descriptive and does not automatically include or exclude sources.
All inclusion decisions are made through manual curation of the source registry.

### Determinism requirement

Given the same version of `config/scope.yaml` and the same source registry file, the system must resolve the identical set of active sources in a stable and reproducible order.

The stable order of resolved sources is defined by sorting on `source_id`.

### Reproducibility

Each execution of the pipeline must persist a snapshot of the resolved scope and active source set.

This ensures that every run can be traced back to the exact configuration used.

### Lead generation model

The system generates candidate leads from the monitored source set.

A lead is an item from an official source that may indicate a TLM relevant real world change, such as:
- a planned road project
- an infrastructure upgrade
- a junction redesign
- a bridge replacement
- a new road section
- another potentially geometry relevant transport infrastructure change

A lead is not treated as confirmed truth.

The MVP does not automatically determine whether the corresponding real world change is already finished or already visible in the target data.

Lead assessment and later confirmation remain separate steps.

### Design rationale

This separation keeps monitoring scope stable while allowing controlled updates to the concrete source list.

Additional cantons should be added through new registry files and configuration, not by changing application logic.