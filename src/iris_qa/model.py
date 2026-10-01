from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Iterable, Literal


class Outcome(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"

    @property
    def rank(self) -> int:
        return _RANK[self]

    @classmethod
    def worst(cls, outcomes: Iterable[Outcome]) -> Outcome:
        return max(outcomes, key=lambda o: o.rank, default=cls.PASS)


_RANK = {Outcome.PASS: 0, Outcome.WARN: 1, Outcome.BLOCK: 2}


@dataclass(frozen=True)
class Violation:
    """One offending record (or record group) and why it offends."""

    issue: str
    severity: Outcome
    country_code: str | None
    key: str | None
    detail: dict[str, Any] = field(default_factory=dict)

    def as_evidence(self) -> dict[str, Any]:
        return {
            "issue": self.issue,
            "severity": self.severity.value,
            "country_code": self.country_code,
            "key": self.key,
            **self.detail,
        }


@dataclass(frozen=True)
class QuarantineEntry:
    country_code: str | None
    key: str | None
    reason: str


@dataclass
class CheckResult:
    check_id: str
    check_type: str
    implementation: Literal["sql", "python"]
    outcome: Outcome
    message: str
    violation_count: int
    issue_counts: dict[str, int]
    evidence: list[dict[str, Any]]
    evidence_truncated: bool
    details: dict[str, Any] = field(default_factory=dict)
    quarantine: list[QuarantineEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        data["quarantine"] = [asdict(q) for q in self.quarantine]
        return data


@dataclass
class RunReport:
    run_id: str
    dataset: str
    profile_name: str
    profile_sha256: str
    as_of: date
    started_at: datetime
    finished_at: datetime
    row_count: int
    dataset_fingerprint: str
    results: list[CheckResult]
    promoted: bool = False

    @property
    def decision(self) -> Outcome:
        return Outcome.worst(r.outcome for r in self.results)

    @property
    def quarantine(self) -> list[QuarantineEntry]:
        """Rows withheld from an otherwise promotable batch; a blocked batch is withheld whole."""
        if self.decision is Outcome.BLOCK:
            return []
        seen: dict[tuple[str | None, str | None], QuarantineEntry] = {}
        for result in self.results:
            for entry in result.quarantine:
                seen.setdefault((entry.country_code, entry.key), entry)
        return sorted(seen.values(), key=lambda e: (e.country_code or "", e.key or ""))

    def result(self, check_id: str) -> CheckResult:
        return next(r for r in self.results if r.check_id == check_id)

    def outcome_counts(self) -> dict[str, int]:
        return {o.value: sum(1 for r in self.results if r.outcome is o) for o in Outcome}

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset": self.dataset,
            "profile": {"name": self.profile_name, "sha256": self.profile_sha256},
            "as_of": self.as_of.isoformat(),
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "row_count": self.row_count,
            "dataset_fingerprint": self.dataset_fingerprint,
            "decision": self.decision.value,
            "promotable": self.decision is not Outcome.BLOCK,
            "promoted": self.promoted,
            "outcome_counts": self.outcome_counts(),
            "blocking_checks": [r.check_id for r in self.results if r.outcome is Outcome.BLOCK],
            "warning_checks": [r.check_id for r in self.results if r.outcome is Outcome.WARN],
            "quarantined_rows": [asdict(q) for q in self.quarantine],
            "checks": [r.to_dict() for r in self.results],
        }
