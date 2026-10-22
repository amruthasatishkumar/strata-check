from datetime import date, datetime, timedelta, timezone

import pandas as pd

from strata_check import Dimension, from_dict, run, to_markdown
from strata_check.checks.estate import audit_readiness, chunk_coverage
from strata_check.checks.tables import ambiguous_names, freshness, row_identity
from strata_check.config import AuditSpec, SourceSpec

NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


def _orders(hours_old: float = 2) -> pd.DataFrame:
    ts = (NOW - timedelta(hours=hours_old)).isoformat()
    return pd.DataFrame({"order_id": [1, 2, 2, None], "total": [10.0, 20.0, 20.0, 5.0],
                         "col1": ["a", "b", "b", "c"], "updated_at": [ts] * 4})


def test_freshness_inside_and_outside_sla():
    src = SourceSpec("orders", updated_column="updated_at", freshness_sla_hours=24)
    assert freshness(src, _orders(2), NOW)[0].score == 100.0
    assert freshness(src, _orders(48), NOW)[0].score == 50.0   # halfway between 1x and 3x SLA
    assert freshness(src, _orders(100), NOW)[0].score == 0.0


def test_row_identity_counts_missing_ids():
    r = row_identity(SourceSpec("orders", id_column="order_id"), _orders())[0]
    assert r.score == 75.0 and r.fix


def test_ambiguous_names_flags_placeholder_columns():
    r = ambiguous_names(SourceSpec("orders"), _orders())[0]
    assert "col1" in r.evidence and r.score == 75.0


def test_chunk_coverage_and_orphans():
    docs = pd.DataFrame({"doc_id": ["a", "b", "c", "d"]})
    chunks = pd.DataFrame({"doc_id": ["a", "a", "b", "z"], "text": ["x" * 500] * 3 + ["short"]})
    by_id = {r.check_id: r for r in chunk_coverage(docs, chunks)}
    assert by_id["index_coverage"].score == 50.0
    assert by_id["chunk_size"].score == 75.0
    assert by_id["chunk_provenance"].dimension == Dimension.TRACEABLE
    assert by_id["chunk_provenance"].score == 75.0


def test_audit_readiness_stale_eval(tmp_path):
    (tmp_path / "evals.jsonl").write_text("{}\n")
    audit = AuditSpec(eval_set="evals.jsonl", last_eval_run=date(2026, 8, 1))
    by_id = {r.check_id: r for r in audit_readiness(audit, tmp_path, today=date(2026, 10, 19))}
    assert by_id["eval_set"].score == 100.0
    assert by_id["eval_recency"].score < 100.0
    assert by_id["agent_logs"].score == 0.0


def test_end_to_end_scorecard():
    cfg = from_dict({"sources": [{
        "name": "orders", "owner": "sales", "system_of_record": "erp",
        "id_column": "order_id", "updated_column": "updated_at", "freshness_sla_hours": 24,
        "upstream": ["erp.orders_raw"],
        "columns": {"order_id": {"description": "Order ID"}, "total": {"description": "Total", "unit": "USD"}},
    }]})
    card = run(cfg, tables={"orders": _orders()}, now=NOW, today=date(2026, 10, 19))
    assert card.dimension_score(Dimension.SOURCED) is not None
    assert card.dimension_score(Dimension.RETRIEVABLE) is None  # no corpus given
    md = to_markdown(card)
    assert "STRATA scorecard" in md and "Top fixes" in md
