# strata-check

Python CLI and library for scoring data against the six STRATA dimensions before use by AI agents or RAG systems. The included student-enrolment dataset is synthetic. This is an early v0.0.1 release, not a deployed service.

## Stack and entry points

- Python 3.10+, setuptools, pandas, PyYAML, and pytest.
- CLI: `src/strata_check/cli.py`, installed as `strata-check`.
- Public Python API: `src/strata_check/__init__.py`.
- Configuration and sample data: `examples/strata.yaml` and `examples/data/`.

## Commands

- Install for development: `python -m pip install -e ".[dev]"`.
- Run the example: `strata-check examples/strata.yaml -o scorecard.md`.
- Test: `python -m pytest`.
- CI tests Python 3.10 and 3.12 using `.github/workflows/ci.yml`.

## Conventions and gotchas

- Source and audit paths are resolved relative to the YAML configuration file.
- Freshness and evaluation-recency scores change with the current date.
- Parquet input requires the optional `parquet` dependency extra.
- Keep credentials, virtual environments, build output, and generated scorecards out of Git.
- Preserve the synthetic examples and MIT license. Do not add customer data.
- Do not use em dashes in written content.

## External tools

Local development does not require MCP tools or cloud credentials. If explicitly needed, use the Microsoft corporate account for WorkIQ, MSX, and Power BI, and the external account for Azure resource management.
