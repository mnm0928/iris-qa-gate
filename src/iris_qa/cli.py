from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from iris_qa import db, engine, report
from iris_qa.checks import ProfileError
from iris_qa.model import Outcome
from iris_qa.profile import DEFAULT_PROFILE_DIR, load_profiles

EXIT_OK, EXIT_WARN, EXIT_BLOCK, EXIT_USAGE = 0, 1, 2, 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="iris-qa", description="Dataset-specific QA gate for IRIS layers")
    parser.add_argument("--dsn", help=f"PostgreSQL DSN (default: $IRIS_QA_DSN or {db.DEFAULT_DSN})")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILE_DIR, help="profile directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="apply SQL migrations")
    sub.add_parser("profiles", help="list profiles and their checks")

    load = sub.add_parser("load", help="replace staging tables with CSV fixtures from a directory")
    load.add_argument("directory", type=Path)

    run = sub.add_parser("run", help="run QA profiles against staging")
    run.add_argument("datasets", nargs="*", help="datasets to check (default: all, in dependency order)")
    run.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="evaluation date (YYYY-MM-DD)")
    run.add_argument("--promote", action="store_true", help="promote non-blocked datasets to curated")
    run.add_argument("--out", type=Path, help="write JSON + Markdown reports to this directory")
    run.add_argument("--evidence-limit", type=int, default=25)
    run.add_argument("--strict", action="store_true", help="exit non-zero on warnings too")

    show = sub.add_parser("show", help="print a persisted run")
    show.add_argument("run_id")
    show.add_argument("--format", choices=("md", "json"), default="md")

    sub.add_parser("history", help="list recent runs")

    args = parser.parse_args(argv)
    try:
        profiles = load_profiles(args.profiles)
    except ProfileError as exc:
        print(f"profile error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    if args.command == "profiles":
        for p in profiles.values():
            deps = f" (after {', '.join(p.depends_on)})" if p.depends_on else ""
            print(f"{p.name}{deps}: {p.description}")
            for c in p.checks:
                print(f"  - {c.check_id:<28} {c.type:<22} [{c.implementation}]")
        return EXIT_OK

    with db.connect(args.dsn) as conn:
        if args.command == "migrate":
            applied = db.migrate(conn)
            print("applied: " + (", ".join(applied) if applied else "nothing (up to date)"))
            return EXIT_OK

        if args.command == "load":
            for p in profiles.values():
                path = args.directory / f"{p.name}.csv"
                if path.exists():
                    n = db.load_csv(conn, p.dataset.staging_table, path)
                    print(f"{p.dataset.staging_table:<22} ← {path} ({n} rows)")
            return EXIT_OK

        if args.command == "show":
            stored = engine.load_report(conn, args.run_id)
            if stored is None:
                print(f"no run {args.run_id}", file=sys.stderr)
                return EXIT_USAGE
            print(report.to_json(stored) if args.format == "json" else report.to_markdown(stored))
            return EXIT_OK

        if args.command == "history":
            for run_id, dataset, decision, promoted, rows, quarantined, started in engine.latest_runs(conn):
                print(f"{started:%Y-%m-%d %H:%M:%S}  {run_id}  {dataset:<12} {decision:<5} "
                      f"rows={rows:<4} quarantined={quarantined:<3} promoted={promoted}")
            return EXIT_OK

        unknown = sorted(set(args.datasets) - set(profiles))
        if unknown:
            print(f"unknown dataset(s): {', '.join(unknown)}; known: {', '.join(profiles)}", file=sys.stderr)
            return EXIT_USAGE
        selected = [p for name, p in profiles.items() if not args.datasets or name in args.datasets]

        results = []
        for profile in selected:
            rep = engine.run(conn, profile, args.as_of, promote=args.promote, evidence_limit=args.evidence_limit)
            data = rep.to_dict()
            results.append(data)
            flag = " → promoted" if rep.promoted else (" → not promoted" if args.promote else "")
            print(f"{report.BADGE[data['decision']]:<9} {rep.dataset:<12} rows={rep.row_count:<4} "
                  f"run={rep.run_id}{flag}")
            for c in rep.results:
                if c.outcome is not Outcome.PASS:
                    print(f"    {c.outcome.value:<5} {c.check_id:<28} {c.message}")
            if args.out:
                report.write(data, args.out)
        if args.out:
            (args.out / "summary.md").write_text(report.summary_markdown(results))
            print(f"reports written to {args.out}/")

        decisions = {r["decision"] for r in results}
        if "BLOCK" in decisions:
            return EXIT_BLOCK
        if args.strict and "WARN" in decisions:
            return EXIT_WARN
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
