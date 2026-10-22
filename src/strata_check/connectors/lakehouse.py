"""Read Delta tables from a Microsoft Fabric Lakehouse (or any folder of Delta tables).

In a Fabric notebook with a default Lakehouse attached, its tables are mounted at
`/lakehouse/default/Tables`, so this works with no credentials:

    import strata_check as sc
    card = sc.run_lakehouse()                      # default Lakehouse
    card = sc.run_lakehouse(config="strata.yaml")  # plus declared owners, SLAs, lineage

What the Lakehouse supplies, so it need not be typed into YAML:

- the tables themselves (a sample of up to `max_rows` rows each),
- column descriptions, from Delta column comments (`ALTER TABLE ... COMMENT`),
- the last write time, from the Delta log, used for freshness when no
  `updated_column` is declared.

Anything declared in the config wins over what is discovered. Needs the `fabric`
extra: `pip install strata-check[fabric]`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from strata_check.config import ColumnSpec, SourceSpec, StrataConfig, load
from strata_check.model import Scorecard

DEFAULT_ROOT = "/lakehouse/default"


def _is_delta(path: Path) -> bool:
    return (path / "_delta_log").is_dir()


def discover(root: str | Path = DEFAULT_ROOT) -> dict[str, str]:
    """Map table name to location for every Delta table under `root/Tables`.

    Schema-enabled Lakehouses nest tables as `Tables/<schema>/<table>`; those are
    named `schema.table`.
    """
    tables_dir = Path(root) / "Tables"
    if not tables_dir.is_dir():
        raise FileNotFoundError(f"No Tables folder under {root}. Is a Lakehouse attached to this notebook?")
    found: dict[str, str] = {}
    for entry in sorted(p for p in tables_dir.iterdir() if p.is_dir()):
        if _is_delta(entry):
            found[entry.name] = str(entry)
        else:
            for sub in sorted(p for p in entry.iterdir() if p.is_dir() and _is_delta(p)):
                found[f"{entry.name}.{sub.name}"] = str(sub)
    return found


def read_table(uri: str, max_rows: int | None = 100_000,
               storage_options: dict[str, str] | None = None):
    """Return (sample DataFrame, column comments, last write time) for one Delta table."""
    from deltalake import DeltaTable

    dt = DeltaTable(uri, storage_options=storage_options)
    dataset = dt.to_pyarrow_dataset()
    data = dataset.head(max_rows) if max_rows else dataset.to_table()
    comments = {f.name: f.metadata["comment"] for f in dt.schema().fields
                if f.metadata and f.metadata.get("comment")}
    history = dt.history(1)
    last = (datetime.fromtimestamp(history[0]["timestamp"] / 1000, tz=timezone.utc)
            if history else None)
    return data.to_pandas(), comments, last


def load_lakehouse(root: str | Path = DEFAULT_ROOT,
                   config: str | Path | StrataConfig | None = None,
                   tables: dict[str, str] | None = None,
                   max_rows: int | None = 100_000,
                   storage_options: dict[str, str] | None = None,
                   ) -> tuple[StrataConfig, dict[str, pd.DataFrame]]:
    """Build a config and DataFrames from a Lakehouse.

    `tables` maps names to Delta locations (e.g. `abfss://` URIs for a Lakehouse
    that isn't attached); without it every table under `root` is discovered.
    Sources declared in `config` but not found in the Lakehouse are left for
    `run` to read from their own `path`.
    """
    cfg = load(config) if isinstance(config, (str, Path)) else config or StrataConfig(sources=[])
    declared = {s.name: s for s in cfg.sources}
    locations = tables if tables is not None else discover(root)
    frames: dict[str, pd.DataFrame] = {}
    for name, uri in locations.items():
        df, comments, last = read_table(uri, max_rows, storage_options)
        src = declared.get(name)
        if src is None:
            src = SourceSpec(name=name)
            cfg.sources.append(src)
        for col, text in comments.items():
            spec = src.columns.setdefault(col, ColumnSpec())
            spec.description = spec.description or text
        src.last_modified = src.last_modified or last
        frames[name] = df
    return cfg, frames


def run_lakehouse(root: str | Path = DEFAULT_ROOT,
                  config: str | Path | StrataConfig | None = None,
                  tables: dict[str, str] | None = None,
                  max_rows: int | None = 100_000,
                  storage_options: dict[str, str] | None = None,
                  now: datetime | None = None) -> Scorecard:
    """Score every table in a Lakehouse. See `load_lakehouse` for the arguments."""
    from strata_check.runner import run

    cfg, frames = load_lakehouse(root, config, tables, max_rows, storage_options)
    return run(cfg, tables=frames, now=now)
