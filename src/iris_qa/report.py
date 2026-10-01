from __future__ import annotations

import json
from pathlib import Path
from typing import Any

UNCERTAINTY_NOTICE = (
    "Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and "
    "based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the "
    "current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental "
    "eligibility and transferability remain subject to project-specific verification. No permit, reservation or "
    "construction readiness is represented."
)

BADGE = {"PASS": "🟢 PASS", "WARN": "🟡 WARN", "BLOCK": "🔴 BLOCK"}
EVIDENCE_ROWS = 10


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=False, default=str) + "\n"


def to_markdown(report: dict[str, Any]) -> str:
    decision = report["decision"]
    out = [
        f"# QA report · `{report['dataset']}` · {BADGE[decision]}",
        "",
        "| | |",
        "|---|---|",
        f"| Run | `{report['run_id']}` |",
        f"| As of | {report['as_of']} |",
        f"| Rows | {report['row_count']} |",
        f"| Dataset fingerprint | `{report['dataset_fingerprint']}` |",
        f"| Profile | `{report['profile']['name']}` (sha256 `{report['profile']['sha256'][:12]}…`) |",
        f"| Decision | **{decision}** — {_verdict(report)} |",
        f"| Promoted | {'yes' if report['promoted'] else 'no'} |",
        f"| Quarantined keys | {len(report['quarantined_rows'])} |",
        "",
        "## Checks",
        "",
        "| # | Check | Impl | Outcome | Violations | Summary |",
        "|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(report["checks"], start=1):
        out.append(
            f"| {i} | `{c['check_id']}` | {c['implementation']} | {BADGE[c['outcome']]} | "
            f"{c['violation_count']} | {_escape(c['message'])} |"
        )

    for c in report["checks"]:
        if c["outcome"] == "PASS":
            continue
        out += ["", f"### {BADGE[c['outcome']]} `{c['check_id']}`", "", _escape(c["message"]), ""]
        if c["issue_counts"]:
            out.append("Issues: " + ", ".join(f"`{k}` × {v}" for k, v in sorted(c["issue_counts"].items())))
            out.append("")
        out += ["| Severity | Issue | Country | Key | Evidence |", "|---|---|---|---|---|"]
        for e in c["evidence"][:EVIDENCE_ROWS]:
            extra = {k: v for k, v in e.items() if k not in ("issue", "severity", "country_code", "key")}
            out.append(
                f"| {e['severity']} | `{e['issue']}` | {e.get('country_code') or '∅'} | "
                f"{_code(e.get('key'))} | {_escape(json.dumps(extra, default=str)) if extra else ''} |"
            )
        shown = min(len(c["evidence"]), EVIDENCE_ROWS)
        if c["evidence_truncated"] or shown < c["violation_count"]:
            out.append(f"\n_{shown} of {c['violation_count']} violations shown; full sample in the JSON report._")

    if report["quarantined_rows"]:
        out += ["", "## Quarantine", "", "Withheld from promotion, all members of each group:", ""]
        out += [f"- `{q['country_code']}` / `{q['key']}` — {q['reason']}" for q in report["quarantined_rows"]]

    out += ["", "---", "", f"> {UNCERTAINTY_NOTICE}", ""]
    return "\n".join(out)


def summary_markdown(reports: list[dict[str, Any]]) -> str:
    out = [
        "# IRIS QA gate · summary",
        "",
        "| Dataset | Decision | Rows | Blocking checks | Warning checks | Quarantined | Promoted |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        out.append(
            f"| [`{r['dataset']}`]({r['dataset']}.md) | {BADGE[r['decision']]} | {r['row_count']} | "
            f"{', '.join(f'`{c}`' for c in r['blocking_checks']) or '—'} | "
            f"{', '.join(f'`{c}`' for c in r['warning_checks']) or '—'} | "
            f"{len(r['quarantined_rows'])} | {'yes' if r['promoted'] else 'no'} |"
        )
    out += ["", f"> {UNCERTAINTY_NOTICE}", ""]
    return "\n".join(out)


def write(report: dict[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{report['dataset']}.json").write_text(to_json(report))
    (directory / f"{report['dataset']}.md").write_text(to_markdown(report))


def _verdict(report: dict[str, Any]) -> str:
    return {
        "PASS": "all checks passed",
        "WARN": "promotable; warnings are reported, unknowns stay NULL",
        "BLOCK": "promotion blocked",
    }[report["decision"]]


def _code(value: Any) -> str:
    return f"`{value}`" if value is not None else "∅"


def _escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")
