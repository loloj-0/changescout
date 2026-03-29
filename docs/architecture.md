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