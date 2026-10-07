"""Test IT general controls over a financial application from system exports."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data"
FILES = {
    "users": ["user", "employee_id", "department", "status", "account_type", "created_date"],
    "user_roles": ["user", "role"],
    "hr_terminations": ["employee_id", "termination_date"],
    "access_reviews": ["quarter", "due_date"],
    "changes": ["change_id", "type", "developer", "deployed_by", "deployed_date"],
    "jobs": ["job_id", "run_date", "status"],
    "restore_tests": ["test_date", "result"],
}
NO_EXCEPTIONS, EXCEPTIONS, NOT_TESTED = "No exceptions", "Exceptions noted", "No population"
_T = {"true", "yes", "y", "1"}


class DataError(ValueError):
    """Raised when an input file cannot be read."""


def _json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_controls() -> dict:
    return _json("controls.json")


def load_sod_rules() -> list[dict]:
    return _json("sod_rules.json")["conflicts"]


def _date(value: str, where: str, required: bool = False) -> date | None:
    value = (value or "").strip()
    if not value:
        if required:
            raise DataError(f"{where}: a date is required.")
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise DataError(f"{where}: dates must look like 2026-03-31, got '{value}'.") from exc


def _rows(text: str, name: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    cols = [(c or "").strip().lower() for c in (reader.fieldnames or [])]
    missing = [c for c in FILES[name] if c not in cols]
    if missing:
        raise DataError(f"{name}.csv is missing required column(s): {', '.join(missing)}.")
    out = []
    for raw in reader:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if any(r.values()):
            out.append(r)
    return out


@dataclass
class Engagement:
    settings: dict
    users: list[dict]
    user_roles: list[dict]
    hr_terminations: list[dict]
    access_reviews: list[dict]
    changes: list[dict]
    jobs: list[dict]
    restore_tests: list[dict]

    @property
    def period(self) -> tuple[date, date]:
        return self.settings["_start"], self.settings["_end"]


def parse_engagement(texts: dict[str, str], settings: dict | None = None) -> Engagement:
    """Build an engagement from CSV texts keyed by file stem (users, changes, ...)."""
    s = _json("settings.json")
    s.pop("_comment", None)
    s.update(settings or {})
    s["_start"] = _date(s["period_start"], "settings period_start", True)
    s["_end"] = _date(s["period_end"], "settings period_end", True)
    if s["_end"] < s["_start"]:
        raise DataError("settings: period_end is before period_start.")
    missing = [n for n in FILES if n not in texts]
    if missing:
        raise DataError(f"Missing input file(s): {', '.join(m + '.csv' for m in missing)}.")
    t = {n: _rows(texts[n], n) for n in FILES}
    for i, u in enumerate(t["users"], 2):
        u["user"] = u["user"].lower()
        u["_created"] = _date(u["created_date"], f"users.csv row {i} created_date", True)
        u["_disabled"] = _date(u.get("disabled_date", ""), f"users.csv row {i} disabled_date")
        u["_last_login"] = _date(u.get("last_login", ""), f"users.csv row {i} last_login")
        u["_approved"] = _date(u.get("access_request_approved_date", ""), f"users.csv row {i} access_request_approved_date")
        u["_privileged"] = u.get("privileged", "").lower() in _T
        u["status"] = u["status"].lower()
        u["account_type"] = u["account_type"].lower()
    for r in t["user_roles"]:
        r["user"] = r["user"].lower()
    for i, h in enumerate(t["hr_terminations"], 2):
        h["_term"] = _date(h["termination_date"], f"hr_terminations.csv row {i}", True)
    for i, a in enumerate(t["access_reviews"], 2):
        a["_due"] = _date(a["due_date"], f"access_reviews.csv row {i} due_date", True)
        a["_done"] = _date(a.get("completed_date", ""), f"access_reviews.csv row {i} completed_date")
    for i, c in enumerate(t["changes"], 2):
        c["type"] = c["type"].lower()
        if c["type"] not in ("standard", "emergency"):
            raise DataError(f"changes.csv row {i}: type must be standard or emergency, got '{c['type']}'.")
        c["_deployed"] = _date(c["deployed_date"], f"changes.csv row {i} deployed_date", True)
        c["_approved"] = _date(c.get("approved_date", ""), f"changes.csv row {i} approved_date")
        for k in ("developer", "approver", "deployed_by"):
            c[k] = c.get(k, "").lower()
    for i, j in enumerate(t["jobs"], 2):
        j["_run"] = _date(j["run_date"], f"jobs.csv row {i}", True)
        j["status"] = j["status"].lower()
    for i, r in enumerate(t["restore_tests"], 2):
        r["_date"] = _date(r["test_date"], f"restore_tests.csv row {i}", True)
    return Engagement(s, **t)


def load_engagement(folder: str | Path) -> Engagement:
    folder = Path(folder)
    if not folder.is_dir():
        raise DataError(f"'{folder}' is not a folder.")
    texts = {n: (folder / f"{n}.csv").read_text(encoding="utf-8-sig") for n in FILES if (folder / f"{n}.csv").exists()}
    settings_file = folder / "settings.json"
    settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
    return parse_engagement(texts, settings)


@dataclass
class Exception_:
    item: str
    detail: str


@dataclass
class ControlResult:
    id: str
    domain: str
    domain_name: str
    objective: str
    procedure: str
    nist: list[str]
    population: int
    result: str
    exceptions: list[Exception_] = field(default_factory=list)

    @property
    def exception_rate(self) -> float:
        return round(100 * len(self.exceptions) / self.population, 1) if self.population else 0.0


@dataclass
class Result:
    organization: str
    system: str
    period_start: str
    period_end: str
    generated_at: str
    tool_version: str
    controls: list[ControlResult]
    sod_roles: list[str]
    sod_matrix: dict[str, dict[str, list[str]]]
    sod_conflicts: list[dict]

    def counts(self) -> dict[str, Any]:
        tested = [c for c in self.controls if c.result != NOT_TESTED]
        return {"controls": len(self.controls), "tested": len(tested),
                "with_exceptions": sum(1 for c in self.controls if c.result == EXCEPTIONS),
                "exceptions": sum(len(c.exceptions) for c in self.controls),
                "sod_users": len({x["user"] for x in self.sod_conflicts}),
                "sod_conflicts": len(self.sod_conflicts)}

    def by_domain(self) -> dict[str, list[ControlResult]]:
        out: dict[str, list[ControlResult]] = {}
        for c in self.controls:
            out.setdefault(c.domain_name, []).append(c)
        return out

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["counts"] = self.counts()
        return d


def _quarters(start: date, end: date) -> list[str]:
    """Calendar quarters that end within the period."""
    out = []
    y, q = start.year, (start.month - 1) // 3 + 1
    while True:
        q_end = date(y, q * 3, 1) + timedelta(days=31)
        q_end = q_end.replace(day=1) - timedelta(days=1)
        if q_end > end:
            break
        if q_end >= start:
            out.append(f"{y}-Q{q}")
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def test_controls(e: Engagement) -> Result:
    from . import __version__

    s = e.settings
    start, end = e.period
    in_period = lambda d: d is not None and start <= d <= end  # noqa: E731
    users = {u["user"]: u for u in e.users}
    by_emp = {}
    for u in e.users:
        if u.get("employee_id"):
            by_emp.setdefault(u["employee_id"], []).append(u)
    active = [u for u in e.users if u["status"] == "active"]
    roles: dict[str, set[str]] = {}
    for r in e.user_roles:
        roles.setdefault(r["user"], set()).add(r["role"])

    tests: dict[str, tuple[int, list[Exception_]]] = {}

    # APD-01 new user access approved before provisioning
    pop = [u for u in e.users if in_period(u["_created"])]
    ex = []
    for u in pop:
        if not u.get("access_request_id") or not u["_approved"]:
            ex.append(Exception_(u["user"], f"Created {u['_created']} with no approved access request on file."))
        elif u["_approved"] > u["_created"]:
            ex.append(Exception_(u["user"], f"Access granted {u['_created']}, approved later on {u['_approved']}."))
    tests["APD-01"] = (len(pop), ex)

    # APD-02 terminations removed promptly and not used afterward
    terms = [h for h in e.hr_terminations if in_period(h["_term"])]
    pop, ex = 0, []
    limit = s["termination_removal_days"]
    for h in terms:
        for u in by_emp.get(h["employee_id"], []):
            pop += 1
            t = h["_term"]
            notes = []
            if u["status"] == "active" or not u["_disabled"]:
                notes.append(f"still active (terminated {t})")
            elif (u["_disabled"] - t).days > limit:
                notes.append(f"disabled {(u['_disabled'] - t).days} days after termination on {t} (allowed {limit})")
            if u["_last_login"] and u["_last_login"] > t:
                notes.append(f"signed in on {u['_last_login']}, after termination")
            if notes:
                ex.append(Exception_(u["user"], "Account " + "; ".join(notes) + "."))
    tests["APD-02"] = (pop, ex)

    # APD-03 quarterly access reviews
    reviews = {a["quarter"]: a for a in e.access_reviews}
    need = _quarters(start, end)
    ex = []
    for q in need:
        a = reviews.get(q)
        if not a:
            ex.append(Exception_(q, "No user access review on file."))
            continue
        if not a["_done"]:
            ex.append(Exception_(q, f"Review due {a['_due']} was not completed."))
        elif a["_done"] > a["_due"]:
            ex.append(Exception_(q, f"Completed {a['_done']}, {(a['_done'] - a['_due']).days} days after the {a['_due']} due date."))
        found = int(a.get("exceptions_found") or 0)
        fixed = int(a.get("exceptions_remediated") or 0)
        if fixed < found:
            ex.append(Exception_(q, f"{found - fixed} of {found} access issues found in the review were not remediated."))
    tests["APD-03"] = (len(need), ex)

    # APD-04 privileged access restricted
    pop = [u for u in active if u["_privileged"]]
    ex = []
    for u in pop:
        if u["account_type"] != "individual":
            ex.append(Exception_(u["user"], f"Administrative privileges on a {u['account_type']} account."))
        elif u["department"] not in s["privileged_departments"]:
            ex.append(Exception_(u["user"], f"Administrative privileges held by {u.get('name') or u['user']} in {u['department']}."))
    tests["APD-04"] = (len(pop), ex)

    # APD-05 segregation of duties
    rules = load_sod_rules()
    sod_roles = sorted({r for rule in rules for r in rule["roles"]})
    matrix = {a: {b: [] for b in sod_roles} for a in sod_roles}
    conflicts, ex = [], []
    for u in sorted(active, key=lambda u: u["user"]):
        held = roles.get(u["user"], set())
        hits = []
        for rule in rules:
            a, b = rule["roles"]
            if a in held and b in held:
                matrix[a][b].append(u["user"])
                matrix[b][a].append(u["user"])
                conflicts.append({"user": u["user"], "name": u.get("name", ""), "department": u["department"],
                                  "roles": [a, b], "risk": rule["risk"]})
                hits.append(f"{a} + {b}")
        if hits:
            ex.append(Exception_(u["user"], "Holds " + "; ".join(hits) + "."))
    tests["APD-05"] = (len(active), ex)

    # APD-06 shared and generic accounts
    ex = [Exception_(u["user"], "Active generic account not assigned to an individual.")
          for u in active if u["account_type"] == "generic"]
    tests["APD-06"] = (len(active), ex)

    changes = [c for c in e.changes if in_period(c["_deployed"])]
    std = [c for c in changes if c["type"] == "standard"]
    emg = [c for c in changes if c["type"] == "emergency"]
    tests["PC-01"] = (len(std), [
        Exception_(c["change_id"], "No approval recorded." if not c["_approved"] else
                   f"Deployed {c['_deployed']}, approved afterward on {c['_approved']}.")
        for c in std if not c["_approved"] or c["_approved"] > c["_deployed"]])
    tests["PC-02"] = (len(changes), [Exception_(c["change_id"], "No evidence of testing before deployment.")
                                      for c in changes if c.get("tested", "").lower() not in _T])
    tests["PC-03"] = (len(changes), [Exception_(c["change_id"], f"Developed and deployed to production by {c['developer']}.")
                                      for c in changes if c["developer"] and c["developer"] == c["deployed_by"]])
    tests["PC-04"] = (len(changes), [Exception_(c["change_id"], f"Developed and approved by {c['developer']}.")
                                      for c in changes if c["developer"] and c["developer"] == c["approver"]])
    days = s["emergency_approval_days"]
    tests["PC-05"] = (len(emg), [
        Exception_(c["change_id"], "Emergency change never approved." if not c["_approved"] else
                   f"Approved {(c['_approved'] - c['_deployed']).days} days after deployment (allowed {days}).")
        for c in emg if not c["_approved"] or (c["_approved"] - c["_deployed"]).days > days])

    failed = [j for j in e.jobs if in_period(j["_run"]) and j["status"] == "failed"]
    tests["CO-01"] = (len(failed), [Exception_(f"{j['job_id']} {j['_run']}",
                                               f"{j.get('job_name') or 'Job'} failed with no follow-up ticket.")
                                    for j in failed if not j.get("ticket_id")])
    ok = [r for r in e.restore_tests if in_period(r["_date"]) and r["result"].lower() == "success"]
    tests["CO-02"] = (1, [] if ok else [Exception_(s["system"], "No successful restore test during the period.")])

    meta = load_controls()
    results = []
    for c in meta["controls"]:
        pop, ex = tests[c["id"]]
        result = NOT_TESTED if pop == 0 else (EXCEPTIONS if ex else NO_EXCEPTIONS)
        results.append(ControlResult(c["id"], c["domain"], meta["domains"][c["domain"]], c["objective"], c["procedure"],
                                     c["nist"], pop, result, ex))
    return Result(s["organization"], s["system"], start.isoformat(), end.isoformat(),
                  datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), __version__, results,
                  sod_roles, matrix, conflicts)
