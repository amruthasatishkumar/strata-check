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

## Status

Early (v0.0.1). Planned: Fabric Lakehouse and Purview metadata connectors, retrieval recall on a question set, HTML report, and data-defect sensitivity tests via `agentdq`.

## Development

Requires Python 3.10 or later.

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

GitHub Actions runs the tests on Python 3.10 and 3.12. Keep credentials and
private datasets out of the repository. The bundled example data is synthetic;
generated `scorecard.md` reports are ignored by Git.


## Licence

MIT
