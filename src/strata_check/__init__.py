"""strata-check: score data on the STRATA dimensions before an AI agent or RAG system uses it."""
from strata_check.config import from_dict, load
from strata_check.connectors.lakehouse import load_lakehouse, run_lakehouse
from strata_check.model import CheckResult, Dimension, Scorecard
from strata_check.runner import run, to_markdown

__all__ = ["CheckResult", "Dimension", "Scorecard", "from_dict", "load", "load_lakehouse", "run", "run_lakehouse",
           "to_markdown"]
__version__ = "0.0.1"
