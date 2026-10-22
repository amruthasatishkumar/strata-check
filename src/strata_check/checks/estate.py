"""Estate-level checks: Retrievable (document chunks) and Audited (evals and logs)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from strata_check.config import AuditSpec
from strata_check.model import CheckResult, Dimension


def chunk_coverage(documents: pd.DataFrame, chunks: pd.DataFrame,
                   doc_id: str = "doc_id", text: str = "text",
                   min_chars: int = 200, max_chars: int = 4000) -> list[CheckResult]:
    """Retrievable: how much of the corpus is indexed, and how usable the chunks are.

    `documents` has one row per source document; `chunks` one row per indexed chunk,
    each carrying the doc_id it came from.
    """
    docs = set(documents[doc_id])
    indexed = docs & set(chunks[doc_id])
    lengths = chunks[text].fillna("").str.len()
    usable = ((lengths >= min_chars) & (lengths <= max_chars)).mean() * 100 if len(chunks) else 0.0
    orphan = int((~chunks[doc_id].isin(docs)).sum())
    cov = 100.0 * len(indexed) / len(docs) if docs else 100.0
    out = [
        CheckResult(Dimension.RETRIEVABLE, "index_coverage", "corpus", round(cov, 1),
                    f"{len(indexed)} of {len(docs)} documents have at least one chunk",
                    "Index the missing documents" if cov < 100 else None),
        CheckResult(Dimension.RETRIEVABLE, "chunk_size", "corpus", round(float(usable), 1),
                    f"{usable:.0f}% of chunks are {min_chars}-{max_chars} characters",
                    "Re-chunk: very short or very long chunks retrieve poorly" if usable < 80 else None),
    ]
    out.append(CheckResult(
        Dimension.TRACEABLE, "chunk_provenance", "corpus", round(100.0 * (1 - orphan / len(chunks)), 1) if len(chunks) else 100.0,
        f"{orphan} chunks point to a document that isn't in the corpus",
        "Drop or re-link orphan chunks so citations resolve" if orphan else None,
    ))
    return out


def audit_readiness(audit: AuditSpec, base_dir: Path, today: date | None = None) -> list[CheckResult]:
    """Audited: an eval set exists, has been run recently, and agent logs are kept."""
    today = today or date.today()
    out = []
    has_eval = bool(audit.eval_set) and (base_dir / audit.eval_set).exists()
    out.append(CheckResult(Dimension.AUDITED, "eval_set", "estate", 100.0 if has_eval else 0.0,
                           f"Eval set {'found at ' + audit.eval_set if has_eval else 'missing'}",
                           None if has_eval else "Create a question set with expected answers"))
    if audit.last_eval_run:
        age = (today - audit.last_eval_run).days
        ok = age <= audit.max_eval_age_days
        out.append(CheckResult(Dimension.AUDITED, "eval_recency", "estate",
                               100.0 if ok else max(0.0, 100.0 - 2 * (age - audit.max_eval_age_days)),
                               f"Last eval run {age} days ago (limit {audit.max_eval_age_days})",
                               None if ok else "Re-run the eval set; schedule it"))
    else:
        out.append(CheckResult(Dimension.AUDITED, "eval_recency", "estate", 0.0,
                               "No eval run recorded", "Run the eval set and record the date"))
    has_logs = bool(audit.agent_logs) and (base_dir / audit.agent_logs).exists()
    out.append(CheckResult(Dimension.AUDITED, "agent_logs", "estate", 100.0 if has_logs else 0.0,
                           f"Agent logs {'found' if has_logs else 'not found'}",
                           None if has_logs else "Log agent questions, retrieved sources and answers"))
    return out
