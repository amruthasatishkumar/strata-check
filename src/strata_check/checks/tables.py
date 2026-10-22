"""Table-level checks for the Sourced, Traceable, Aligned and Timely dimensions.

Each check takes a SourceSpec and its DataFrame and returns CheckResults.
Scores are 0-100; evidence says what was measured, fix says what to do.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd

from strata_check.config import SourceSpec
from strata_check.model import CheckResult, Dimension

# Column names that tell an agent nothing about meaning.
AMBIGUOUS_NAME = re.compile(r"^(col|column|field|var|attr|data|value|val|tmp|temp|x|unnamed)[_\s]?\d*$", re.I)


def _pct(n: float, d: float) -> float:
    return round(100.0 * n / d, 1) if d else 100.0


# ---------------- Sourced ----------------

def ownership(src: SourceSpec, df: pd.DataFrame) -> list[CheckResult]:
    declared = [bool(src.owner), bool(src.system_of_record)]
    missing = [k for k, ok in zip(("owner", "system_of_record"), declared) if not ok]
    return [CheckResult(
        Dimension.SOURCED, "ownership", src.name, _pct(sum(declared), 2),
        f"Declared: {', '.join(k for k, ok in zip(('owner', 'system_of_record'), declared) if ok) or 'none'}",
        f"Declare {' and '.join(missing)} so agents only answer from authoritative data" if missing else None,
    )]


def duplicate_entities(src: SourceSpec, df: pd.DataFrame) -> list[CheckResult]:
    if not src.id_column or src.id_column not in df:
        return []
    dup = int(df[src.id_column].duplicated().sum())
    return [CheckResult(
        Dimension.SOURCED, "duplicate_entities", src.name, 100.0 - _pct(dup, len(df)),
        f"{dup} of {len(df)} rows repeat an existing {src.id_column}",
        "Deduplicate on the ID column or mark one copy as the system of record" if dup else None,
    )]


# ---------------- Traceable ----------------

def row_identity(src: SourceSpec, df: pd.DataFrame) -> list[CheckResult]:
    if not src.id_column:
        return [CheckResult(Dimension.TRACEABLE, "row_identity", src.name, 0.0,
                            "No id_column declared, so an answer can't cite the row it came from",
                            "Declare a stable id_column")]
    if src.id_column not in df:
        return [CheckResult(Dimension.TRACEABLE, "row_identity", src.name, 0.0,
                            f"Declared id_column '{src.id_column}' is not in the data",
                            "Fix the id_column name or add the column")]
    null = int(df[src.id_column].isna().sum())
    return [CheckResult(
        Dimension.TRACEABLE, "row_identity", src.name, 100.0 - _pct(null, len(df)),
        f"{null} of {len(df)} rows have no {src.id_column}",
        "Backfill missing IDs so every answer is traceable" if null else None,
    )]


def lineage(src: SourceSpec, df: pd.DataFrame) -> list[CheckResult]:
    ok = bool(src.upstream)
    return [CheckResult(
        Dimension.TRACEABLE, "lineage", src.name, 100.0 if ok else 0.0,
        f"Upstream: {', '.join(src.upstream)}" if ok else "No upstream lineage declared",
        None if ok else "Record upstream sources (or pull lineage from your catalog)",
    )]


# ---------------- Aligned ----------------

def column_documentation(src: SourceSpec, df: pd.DataFrame) -> list[CheckResult]:
    cols = list(df.columns)
    documented = [c for c in cols if c in src.columns and src.columns[c].description]
    missing = [c for c in cols if c not in documented]
    return [CheckResult(
        Dimension.ALIGNED, "column_documentation", src.name, _pct(len(documented), len(cols)),
        f"{len(documented)} of {len(cols)} columns have a business description",
        f"Describe: {', '.join(missing[:5])}{' …' if len(missing) > 5 else ''}" if missing else None,
    )]


def numeric_units(src: SourceSpec, df: pd.DataFrame) -> list[CheckResult]:
    nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != src.id_column]
    if not nums:
        return []
    with_unit = [c for c in nums if c in src.columns and src.columns[c].unit]
    missing = [c for c in nums if c not in with_unit]
    return [CheckResult(
        Dimension.ALIGNED, "numeric_units", src.name, _pct(len(with_unit), len(nums)),
        f"{len(with_unit)} of {len(nums)} numeric columns declare a unit",
        f"Declare units for: {', '.join(missing[:5])}" if missing else None,
    )]


def ambiguous_names(src: SourceSpec, df: pd.DataFrame) -> list[CheckResult]:
    bad = [c for c in df.columns if AMBIGUOUS_NAME.match(str(c))]
    return [CheckResult(
        Dimension.ALIGNED, "ambiguous_names", src.name, 100.0 - _pct(len(bad), len(df.columns)),
        f"{len(bad)} column names carry no meaning" + (f": {', '.join(map(str, bad))}" if bad else ""),
        "Rename to business terms an agent can map to questions" if bad else None,
    )]


# ---------------- Timely ----------------

def freshness(src: SourceSpec, df: pd.DataFrame, now: datetime | None = None) -> list[CheckResult]:
    if not src.updated_column or src.updated_column not in df:
        return [CheckResult(Dimension.TIMELY, "freshness", src.name, 0.0,
                            "No updated_column, so freshness can't be measured",
                            "Declare a last-updated timestamp column")]
    now = now or datetime.now(timezone.utc)
    latest = pd.to_datetime(df[src.updated_column], utc=True, errors="coerce").max()
    if pd.isna(latest):
        return [CheckResult(Dimension.TIMELY, "freshness", src.name, 0.0,
                            f"{src.updated_column} has no parseable timestamps", "Fix the timestamp column")]
    age_h = (now - latest.to_pydatetime()).total_seconds() / 3600
    if src.freshness_sla_hours is None:
        return [CheckResult(Dimension.TIMELY, "freshness", src.name, 50.0,
                            f"Newest row is {age_h:.1f} h old; no SLA declared",
                            "Declare freshness_sla_hours so staleness can be judged")]
    sla = src.freshness_sla_hours
    # Full marks inside the SLA, falling linearly to 0 at 3x the SLA.
    score = 100.0 if age_h <= sla else max(0.0, 100.0 * (1 - (age_h - sla) / (2 * sla)))
    return [CheckResult(
        Dimension.TIMELY, "freshness", src.name, round(score, 1),
        f"Newest row is {age_h:.1f} h old against a {sla:g} h SLA",
        None if age_h <= sla else "Refresh the source or relax the SLA deliberately",
    )]


TABLE_CHECKS = [ownership, duplicate_entities, row_identity, lineage,
                column_documentation, numeric_units, ambiguous_names, freshness]
