"""Run every STRATA check over a config and render the scorecard."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from strata_check.checks.estate import audit_readiness
from strata_check.checks.tables import TABLE_CHECKS, freshness
from strata_check.config import StrataConfig
from strata_check.model import Dimension, Scorecard


def _read(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def run(cfg: StrataConfig, tables: dict[str, pd.DataFrame] | None = None,
        now: datetime | None = None, today: date | None = None) -> Scorecard:
    """Score every source. Pass `tables` to supply DataFrames directly
    (e.g. from Spark in a Fabric notebook) instead of reading `path`."""
    tables = tables or {}
    card = Scorecard()
    for src in cfg.sources:
        df = tables.get(src.name)
        if df is None:
            if not src.path:
                raise ValueError(f"Source '{src.name}' has no path and no DataFrame was given")
            df = _read(cfg.base_dir / src.path)
        for check in TABLE_CHECKS:
            card.results += check(src, df, now) if check is freshness else check(src, df)
    card.results += audit_readiness(cfg.audit, cfg.base_dir, today)
    return card


def to_markdown(card: Scorecard) -> str:
    lines = ["# STRATA scorecard", "", f"**Overall: {card.overall()} / 100**", "",
             "| Dimension | Score |", "|---|---|"]
    for d in Dimension:
        s = card.dimension_score(d)
        lines.append(f"| {d.value} | {'not measured' if s is None else s} |")
    lines += ["", "## Top fixes", ""]
    fixes = card.top_fixes()
    lines += [f"1. **{r.dimension.value} / {r.source}**: {r.fix} ({r.evidence})" for r in fixes] or ["None."]
    lines += ["", "## All checks", "", "| Dimension | Source | Check | Score | Evidence |", "|---|---|---|---|---|"]
    lines += [f"| {r.dimension.value} | {r.source} | {r.check_id} | {r.score} | {r.evidence} |" for r in card.results]
    return "\n".join(lines) + "\n"
