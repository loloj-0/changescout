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
The file `config/scope.yaml` defines the active monitoring context.

It contains:
- `version`
- `canton_id`
- `languages`
- `time_window_days`
- `source_registry`
- `source_policy`

This file determines which registry is used and under which policy the monitoring run operates.

### Source registry
The file `config/sources/<registry>.yaml` defines the concrete sources for a registry.

Each source entry contains:
- `source_id`
- `name`
- `base_url`
- `crawl_type`
- `crawl_frequency_hours`
- `active`

This file determines which exact endpoints are considered part of the monitored source set.

### Design rationale
This separation keeps the conceptual scope stable while allowing controlled updates to the concrete source list.
New cantons should be added by creating new source registries and selecting them through configuration, not by changing application logic.