"""Command line: strata-check [path/to/strata.yaml] [--lakehouse PATH] [-o scorecard.md]"""
from __future__ import annotations

import argparse
import sys

from strata_check import load, run, run_lakehouse, to_markdown


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="strata-check", description=__doc__)
    p.add_argument("config", nargs="?", help="YAML with declared owners, SLAs and lineage")
    p.add_argument("--lakehouse", metavar="PATH",
                   help="score every Delta table under PATH/Tables (e.g. /lakehouse/default)")
    p.add_argument("-o", "--output", help="write the Markdown scorecard here (default: stdout)")
    p.add_argument("--fail-under", type=float, help="exit 1 if the overall score is below this")
    a = p.parse_args(argv)
    if a.lakehouse:
        card = run_lakehouse(a.lakehouse, config=a.config)
    elif a.config:
        card = run(load(a.config))
    else:
        p.error("give a config file, --lakehouse PATH, or both")
    md = to_markdown(card)
    if a.output:
        with open(a.output, "w") as f:
            f.write(md)
    else:
        sys.stdout.write(md)
    overall = card.overall() or 0
    return 1 if a.fail_under is not None and overall < a.fail_under else 0


if __name__ == "__main__":
    raise SystemExit(main())
