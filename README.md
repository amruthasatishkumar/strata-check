# strata-check

Score your data on the six **STRATA** dimensions before an AI agent or RAG system relies on it.

STRATA (A Layered Data Architecture for Reliable Enterprise AI) holds that reliable enterprise AI needs more than clean data:

| Dimension | Question | Checks in this release |
|---|---|---|
| **Sourced** | Is the data authoritative? | owner and system of record declared; duplicate entities |
| **Traceable** | Can an answer be traced to its origin? | stable row IDs; declared lineage; chunk provenance |
| **Retrievable** | Can the AI find what it needs? | index coverage; chunk size |
| **Aligned** | Is the data tied to business meaning? | column descriptions; numeric units; ambiguous names |
| **Timely** | Is it current enough? | freshness against a declared SLA |
| **Audited** | Is reliability measured continuously? | eval set present and recent; agent logs kept |

## Quick start

```bash
pip install -e .
strata-check examples/strata.yaml -o scorecard.md
```

The example scores a synthetic student-enrolment table. In a notebook (including Microsoft Fabric), pass DataFrames directly:

```python
import strata_check as sc
cfg = sc.load("strata.yaml")
card = sc.run(cfg, tables={"enrolments": df})
print(sc.to_markdown(card))
```

Use `--fail-under 80` to fail a CI pipeline when data falls below a STRATA score.

## Microsoft Fabric Lakehouse

In a Fabric notebook with a Lakehouse attached, score every table in it with one call:

```python
%pip install "strata-check[fabric]"

import strata_check as sc
card = sc.run_lakehouse()                      # tables under /lakehouse/default/Tables
card = sc.run_lakehouse(config="strata.yaml")  # add declared owners, SLAs and lineage
print(sc.to_markdown(card))
```

The Lakehouse supplies what you would otherwise declare by hand:

- **Tables:** every Delta table, including `schema.table` in schema-enabled Lakehouses, sampled up to `max_rows` (default 100,000).
- **Column descriptions:** taken from Delta column comments (`ALTER TABLE ... ALTER COLUMN ... COMMENT '...'`). They feed the Aligned score.
- **Last write time:** taken from the Delta log. It drives the Timely score when no `updated_column` is declared.

Anything in your YAML wins over what is discovered. For a Lakehouse that isn't attached, pass `tables={"orders": "abfss://..."}` and `storage_options`. From the command line, run `strata-check --lakehouse /lakehouse/default [strata.yaml]`.

## Status

Early (v0.0.1). Planned: Purview metadata connector, retrieval recall on a question set, HTML report, and data-defect sensitivity tests via `agentdq`.

## Development

Requires Python 3.10 or later.

```bash
python -m pip install -e ".[dev,fabric]"
python -m pytest
```

GitHub Actions runs the tests on Python 3.10 and 3.12. Keep credentials and
private datasets out of the repository. The bundled example data is synthetic;
generated `scorecard.md` reports are ignored by Git.


## Licence

MIT
