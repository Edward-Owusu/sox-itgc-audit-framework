"""Command-line interface.

Examples:
    sox-itgc samples/granite_peak
    sox-itgc engagement_folder --format html md csv --out workpapers --fail-on-deficiency
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .engine import EXCEPTIONS, DataError, load_engagement, test_controls
from .reporting import WRITERS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sox-itgc", description="Test SOX IT general controls from system exports.")
    p.add_argument("folder", help="Engagement folder with settings.json and the input CSV files")
    p.add_argument("--format", nargs="+", choices=sorted(WRITERS), default=["html", "csv"])
    p.add_argument("--out", default="reports", help="Output directory (default: reports)")
    p.add_argument("--fail-on-deficiency", action="store_true", help="Exit with code 2 if any control has exceptions")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        r = test_controls(load_engagement(args.folder))
    except (OSError, DataError, ValueError) as exc:
        print(f"Could not read input: {exc}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.folder).resolve().name + "_itgc"
    for fmt in args.format:
        path = out / f"{stem}.{fmt}"
        path.write_text(WRITERS[fmt](r), encoding="utf-8")
        print(f"Wrote {path}")
    k = r.counts()
    print(f"\n{r.organization} | {r.system} | {r.period_start} to {r.period_end}")
    print(f"Controls tested: {k['tested']}/{k['controls']} | with exceptions: {k['with_exceptions']} | "
          f"exceptions: {k['exceptions']} | SoD conflicts: {k['sod_conflicts']}")
    for c in r.controls:
        print(f"  {c.id:<7} {c.result:<17} {len(c.exceptions):>2} of {c.population:<3} {c.objective}")
    if args.fail_on_deficiency and any(c.result == EXCEPTIONS for c in r.controls):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
