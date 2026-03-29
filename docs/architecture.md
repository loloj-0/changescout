# Architecture

## MVP Scope Decision

The MVP monitoring scope is limited to a single canton.

### Selected canton
Uri

### Scope policy
The system monitors only manually curated official canton level publication sources for the selected canton.

### Included in MVP
- one canton only
- manual source curation
- official canton level web sources
- versioned scope configuration in Git
- deterministic source selection from config

### Explicitly excluded from MVP
- municipalities
- unofficial media sources
- associations and private organizations
- social media channels
- automatic source discovery
- cross canton support in runtime behavior

### Rationale
The MVP prioritizes determinism, reviewability, and low operational complexity.
A narrow and explicit source boundary is required so that the same configuration always resolves to the same source set.

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

Each source entry contains:
- `source_id`
- `name`
- `base_url`
- `crawl_type`
- `crawl_frequency_hours`
- `active`

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

### Design rationale

This separation keeps monitoring scope stable while allowing controlled updates to the concrete source list.
Additional cantons should be added through new registry files and configuration, not by changing application logic.