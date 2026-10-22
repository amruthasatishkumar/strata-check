from datetime import datetime, timedelta, timezone

import pytest

pa = pytest.importorskip("pyarrow")
deltalake = pytest.importorskip("deltalake")

from strata_check import Dimension, from_dict, load_lakehouse, run_lakehouse  # noqa: E402
from strata_check.cli import main  # noqa: E402
from strata_check.connectors.lakehouse import discover  # noqa: E402


def _write(path, comments=None):
    comments = comments or {}
    schema = pa.schema([
        pa.field(name, typ, metadata={"comment": comments[name]} if name in comments else None)
        for name, typ in [("student_id", pa.int64()), ("course", pa.string()), ("col1", pa.string())]
    ])
    data = pa.table({"student_id": [1, 2, 3], "course": ["A", "B", "B"], "col1": ["x", "y", "z"]},
                    schema=schema)
    deltalake.write_deltalake(str(path), data)


@pytest.fixture
def lakehouse(tmp_path):
    tables = tmp_path / "Tables"
    _write(tables / "enrolments", {"student_id": "Pseudonymous student ID", "course": "Course code"})
    _write(tables / "sales" / "orders")  # schema-enabled layout: Tables/<schema>/<table>
    (tables / "not_a_table").mkdir()
    return tmp_path


def test_discover_finds_flat_and_schema_tables(lakehouse):
    assert list(discover(lakehouse)) == ["enrolments", "sales.orders"]


def test_discover_explains_missing_tables_folder(tmp_path):
    with pytest.raises(FileNotFoundError, match="Lakehouse attached"):
        discover(tmp_path)


def test_column_comments_become_descriptions(lakehouse):
    cfg, frames = load_lakehouse(lakehouse)
    enrol = next(s for s in cfg.sources if s.name == "enrolments")
    assert enrol.columns["course"].description == "Course code"
    assert enrol.last_modified is not None
    assert len(frames["enrolments"]) == 3

    card = run_lakehouse(lakehouse)
    docs = {r.source: r.score for r in card.results if r.check_id == "column_documentation"}
    assert docs == {"enrolments": 66.7, "sales.orders": 0.0}


def test_declared_metadata_wins_and_write_time_drives_freshness(lakehouse):
    cfg = from_dict({"sources": [{
        "name": "enrolments", "owner": "registrar", "freshness_sla_hours": 24,
        "columns": {"course": {"description": "Registered course code"}},
    }]})
    cfg, _ = load_lakehouse(lakehouse, config=cfg)
    enrol = next(s for s in cfg.sources if s.name == "enrolments")
    assert enrol.columns["course"].description == "Registered course code"
    assert enrol.columns["student_id"].description == "Pseudonymous student ID"

    fresh = [r for r in run_lakehouse(lakehouse, config=cfg).results
             if r.dimension is Dimension.TIMELY and r.source == "enrolments"][0]
    assert fresh.score == 100.0 and fresh.evidence.startswith("Last table write")

    later = datetime.now(timezone.utc) + timedelta(hours=100)
    stale = [r for r in run_lakehouse(lakehouse, config=cfg, now=later).results
             if r.dimension is Dimension.TIMELY and r.source == "enrolments"][0]
    assert stale.score == 0.0


def test_max_rows_samples_large_tables(lakehouse):
    _, frames = load_lakehouse(lakehouse, max_rows=2)
    assert len(frames["enrolments"]) == 2


def test_cli_lakehouse(lakehouse, tmp_path):
    out = tmp_path / "card.md"
    assert main(["--lakehouse", str(lakehouse), "-o", str(out)]) == 0
    assert "sales.orders" in out.read_text()
