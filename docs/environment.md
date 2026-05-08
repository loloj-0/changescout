# Environment

## Python

ChangeScout is tested with Python 3.9.

Python 3.9+ should work as long as the dependency set remains compatible.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install project and development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

Optional local LLM dependencies are installed separately because CUDA and hardware environments differ:

```bash
python -m pip install -r requirements-llm.txt
```

## Validation

Run tests:

```bash
PYTHONPATH=src pytest -q
```

Run the CLI help:

```bash
PYTHONPATH=src python -m changescout.cli --help
```

Validate a source registry:

```bash
PYTHONPATH=src python -m changescout.cli validate-registry \
  --config-dir config \
  --source-registry zh
```

## Generated data

Operational run outputs are written to `artifacts/runs/<run_id>/`.

Raw crawled HTML is written to `data/crawling/<run_id>/`.

Both paths are ignored by Git.
