"""Declared metadata about each data source, loaded from YAML or a dict.

Example:

    sources:
      - name: orders
        path: data/orders.csv
        owner: sales-data-team
        system_of_record: erp
        id_column: order_id
        updated_column: updated_at
        freshness_sla_hours: 24
        upstream: [erp.orders_raw]
        columns:
          order_id: {description: Unique order identifier}
          total: {description: Order total, unit: USD}
    audit:
      eval_set: evals/questions.jsonl
      last_eval_run: 2026-10-15
      agent_logs: logs/agent/
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass
class ColumnSpec:
    description: str | None = None
    unit: str | None = None


@dataclass
class SourceSpec:
    name: str
    path: str | None = None
    owner: str | None = None
    system_of_record: str | None = None
    id_column: str | None = None
    updated_column: str | None = None
    freshness_sla_hours: float | None = None
    upstream: list[str] = field(default_factory=list)
    columns: dict[str, ColumnSpec] = field(default_factory=dict)
    # Set by connectors from table metadata (e.g. the Delta log), not usually by hand.
    last_modified: datetime | None = None


@dataclass
class AuditSpec:
    eval_set: str | None = None
    last_eval_run: date | None = None
    agent_logs: str | None = None
    max_eval_age_days: int = 30


@dataclass
class StrataConfig:
    sources: list[SourceSpec]
    audit: AuditSpec = field(default_factory=AuditSpec)
    base_dir: Path = Path(".")


def _source(d: dict[str, Any]) -> SourceSpec:
    cols = {k: ColumnSpec(**(v or {})) for k, v in (d.pop("columns", None) or {}).items()}
    return SourceSpec(**d, columns=cols)


def from_dict(d: dict[str, Any], base_dir: Path | str = ".") -> StrataConfig:
    audit = d.get("audit") or {}
    if isinstance(audit.get("last_eval_run"), str):
        audit["last_eval_run"] = date.fromisoformat(audit["last_eval_run"])
    return StrataConfig(
        sources=[_source(dict(s)) for s in d.get("sources", [])],
        audit=AuditSpec(**audit),
        base_dir=Path(base_dir),
    )


def load(path: str | Path) -> StrataConfig:
    import yaml

    path = Path(path)
    with path.open() as f:
        return from_dict(yaml.safe_load(f) or {}, base_dir=path.parent)
