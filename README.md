# ChangeScout

ChangeScout is a deterministic monitoring pipeline for canton scoped source observation.

## Initial MVP goal

The first MVP defines the monitoring scope for one canton in a reproducible way.
The system must resolve the same active source set from the same config.

## Project structure

- `src/changescout/` application code
- `config/` scope and source registry
- `tests/` automated tests
- `docs/` architecture and environment notes
