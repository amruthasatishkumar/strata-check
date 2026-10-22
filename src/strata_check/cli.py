"""Command line: strata-check path/to/strata.yaml [-o scorecard.md]"""
from __future__ import annotations

import argparse
import sys

from strata_check import load, run, to_markdown


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="strata-check", description=__doc__)
    p.add_argument("config")
    p.add_argument("-o", "--output", help="write the Markdown scorecard here (default: stdout)")
    p.add_argument("--fail-under", type=float, help="exit 1 if the overall score is below this")
    a = p.parse_args(argv)
    card = run(load(a.config))
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
