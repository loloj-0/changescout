# Environment

## Python

- Python 3.9+

## Setup

Create virtual environment:

`python -m venv .venv`

Activate:

`source .venv/bin/activate`

Install project and dev dependencies:

`pip install -e .[dev]`

## Validation

Run tests:

`pytest`

Run CLI:

`changescout --config-dir config --snapshot-dir artifacts`