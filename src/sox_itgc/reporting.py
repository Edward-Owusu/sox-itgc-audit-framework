"""Write ITGC testing results as a worksheet (HTML), Markdown, CSV, or JSON."""

from __future__ import annotations

import csv
import io
import json
from html import escape

from .engine import EXCEPTIONS, NO_EXCEPTIONS, NOT_TESTED, Result

DISCLAIMER = (
    "This worksheet records automated tests of the data supplied. Exceptions are observations for the auditor to "
    "evaluate; classifying deficiencies (control deficiency, significant deficiency, or material weakness) requires "
    "professional judgment about compensating controls and financial statement impact. The tool does not express an "
    "opinion on internal control over financial reporting."
)
RESULT_CLASS = {NO_EXCEPTIONS: "ok", EXCEPTIONS: "ex", NOT_TESTED: "na"}

MATRIX_CSS = """
.sod{border-collapse:separate;border-spacing:3px;font:12px/1.3 "Segoe UI",Roboto,Arial,sans-serif}
.sod th{font-weight:600;color:#3f5246;padding:4px;vertical-align:bottom}
.sod th.col{writing-mode:vertical-rl;transform:rotate(180deg);text-align:left;height:150px;white-space:nowrap}
.sod th.row{text-align:right;white-space:nowrap;padding-right:8px}
.sod td{width:42px;height:34px;text-align:center;border-radius:5px;font-weight:700}
.sod td.nc{background:#f1f3ee;color:#c3cbc2}
.sod td.ok{background:#dcebd9;color:#2f6b3a}
.sod td.hit{background:#b42318;color:#fff}
.sod td.self{background:transparent}
"""


def sod_matrix_html(r: Result) -> str:
    """Role-by-role grid. Green: incompatible pair with no users holding both. Red: users holding both."""
    from .engine import load_sod_rules

    pairs = {frozenset(x["roles"]) for x in load_sod_rules()}
    e = escape
    head = "".join(f'<th class="col">{e(c)}</th>' for c in r.sod_roles)
    rows = []
    for a in r.sod_roles:
        cells = []
        for b in r.sod_roles:
            if a == b:
                cells.append('<td class="self"></td>')
            elif frozenset((a, b)) not in pairs:
                cells.append('<td class="nc" title="Compatible">·</td>')
            else:
                who = r.sod_matrix[a][b]
                cells.append(f'<td class="hit" title="{e(", ".join(who))}">{len(who)}</td>' if who
                             else '<td class="ok" title="Incompatible pair: no users hold both">0</td>')
        rows.append(f'<tr><th class="row">{e(a)}</th>{"".join(cells)}</tr>')
    return f'<table class="sod"><tr><th></th>{head}</tr>{"".join(rows)}</table>'


def to_json(r: Result) -> str:
    d = r.to_dict()
    for c, raw in zip(d["controls"], r.controls):
        c["exception_rate"] = raw.exception_rate
    return json.dumps(d, indent=2, default=str)


def to_csv(r: Result) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["control", "domain", "objective", "test_procedure", "population", "exceptions", "result", "item", "detail", "nist"])
    for c in r.controls:
        if c.exceptions:
            for x in c.exceptions:
                w.writerow([c.id, c.domain_name, c.objective, c.procedure, c.population, len(c.exceptions), c.result,
                            x.item, x.detail, "; ".join(c.nist)])
        else:
            w.writerow([c.id, c.domain_name, c.objective, c.procedure, c.population, 0, c.result, "", "", "; ".join(c.nist)])
    return buf.getvalue()


def to_markdown(r: Result) -> str:
    k = r.counts()
    L = [f"# ITGC testing worksheet: {r.organization}", "",
         f"System: {r.system} | Period {r.period_start} to {r.period_end} | Generated {r.generated_at}", "",
         f"- Controls tested: **{k['tested']} of {k['controls']}**",
         f"- Controls with exceptions: **{k['with_exceptions']}** ({k['exceptions']} exceptions in total)",
         f"- Segregation-of-duties conflicts: **{k['sod_conflicts']}** across {k['sod_users']} user(s)", ""]
    for domain, controls in r.by_domain().items():
        L += [f"## {domain}", "", "| Control | Objective | Population | Exceptions | Result |", "|---|---|---|---|---|"]
        L += [f"| {c.id} | {c.objective} | {c.population} | {len(c.exceptions)} | {c.result} |" for c in controls]
        L.append("")
    L += ["## Exceptions", ""]
    for c in r.controls:
        for x in c.exceptions:
            L.append(f"- **{c.id}** `{x.item}`: {x.detail}")
    if not any(c.exceptions for c in r.controls):
        L.append("No exceptions.")
    L += ["", "## Segregation-of-duties conflicts", ""]
    L += [f"- **{x['user']}** ({x['department']}): {x['roles'][0]} + {x['roles'][1]}. {x['risk']}" for x in r.sod_conflicts] or ["None."]
    L += ["", f"_{DISCLAIMER}_", ""]
    return "\n".join(L)


_CSS = """
*{box-sizing:border-box}
body{margin:0;background:#fbfaf5;color:#14231a;font:14px/1.55 "Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
main{max-width:1100px;margin:0 auto;padding:30px 24px 60px}
.sheet{background:#fff;border:1px solid #d9e3d5;border-top:6px solid #166534;border-radius:8px;padding:22px 26px}
.kick{text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:#166534;font-weight:700;margin:0}
h1{font-family:Georgia,"Times New Roman",serif;font-size:28px;margin:4px 0 8px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:6px 24px;color:#3f5246;border-top:1px solid #e6ece3;padding-top:10px}
.meta b{color:#14231a}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0 6px}
.tile{border:1px solid #d9e3d5;border-radius:8px;padding:12px 14px;background:#f7faf5}
.tile b{display:block;font-size:26px;font-family:Georgia,serif}.tile span{color:#3f5246;font-size:12.5px}
h2{font-family:Georgia,serif;font-size:20px;color:#166534;margin:32px 0 10px}
.table-wrap{overflow-x:auto}
table.ws{border-collapse:collapse;width:100%;background:#fff}
.ws th{background:#e7efe3;color:#14231a;text-align:left;padding:8px 10px;border:1px solid #d0dccb;font-size:12.5px}
.ws td{padding:8px 10px;border:1px solid #e1e8dd;vertical-align:top}
.ws td.num{text-align:center;font-variant-numeric:tabular-nums}
.res{display:inline-block;padding:1px 8px;border-radius:3px;font-size:12px;font-weight:700;white-space:nowrap}
.res.ok{background:#dcebd9;color:#1d5a2a}.res.ex{background:#fde4dc;color:#9a2a14}.res.na{background:#eceee9;color:#6b7563}
.proc{color:#4f6156;font-size:12.5px}
.exl{margin:6px 0 0;padding-left:18px;color:#7a2a17;font-size:12.5px}
.exl code{background:#fbefe9;padding:0 4px;border-radius:3px}
.legend{color:#4f6156;font-size:12.5px;margin-top:8px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin:0 4px 0 12px}
.sign{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:30px}
.sign div{border-top:1px solid #9fb19a;padding-top:6px;color:#4f6156;font-size:12.5px}
.note{color:#4f6156;font-size:12.5px;margin-top:24px}
"""


def to_html(r: Result) -> str:
    e = escape
    k = r.counts()
    sections = []
    for domain, controls in r.by_domain().items():
        rows = []
        for c in controls:
            exl = ("<ul class='exl'>" + "".join(f"<li><code>{e(x.item)}</code> {e(x.detail)}</li>" for x in c.exceptions)
                   + "</ul>") if c.exceptions else ""
            rows.append(f"<tr><td><b>{e(c.id)}</b></td><td>{e(c.objective)}<div class='proc'>Test: {e(c.procedure)}</div>{exl}</td>"
                        f"<td class='num'>{c.population}</td><td class='num'>{len(c.exceptions)}</td>"
                        f"<td><span class='res {RESULT_CLASS[c.result]}'>{e(c.result)}</span></td>"
                        f"<td>{e(', '.join(c.nist))}</td></tr>")
        sections.append(f"<h2>{e(domain)}</h2><div class='table-wrap'><table class='ws'><thead><tr><th>Ref</th>"
                        f"<th>Control objective and test performed</th><th>Population</th><th>Exceptions</th><th>Result</th>"
                        f"<th>NIST 800-53</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    conflicts = "".join(f"<tr><td>{e(x['user'])}</td><td>{e(x['name'])}</td><td>{e(x['department'])}</td>"
                        f"<td>{e(x['roles'][0])} + {e(x['roles'][1])}</td><td>{e(x['risk'])}</td></tr>" for x in r.sod_conflicts)
    conflicts = (f"<div class='table-wrap'><table class='ws'><thead><tr><th>User</th><th>Name</th><th>Department</th>"
                 f"<th>Conflicting roles</th><th>Risk</th></tr></thead><tbody>{conflicts}</tbody></table></div>"
                 if conflicts else "<p>No users hold incompatible roles.</p>")
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ITGC testing worksheet: {e(r.organization)}</title><style>{_CSS}{MATRIX_CSS}</style></head><body><main>
<div class="sheet"><p class="kick">IT general controls testing worksheet</p><h1>{e(r.organization)}</h1>
<div class="meta"><span>System: <b>{e(r.system)}</b></span><span>Period: <b>{e(r.period_start)} to {e(r.period_end)}</b></span>
<span>Prepared: <b>{e(r.generated_at)}</b></span><span>Tool: <b>sox_itgc {e(r.tool_version)}</b></span></div>
<div class="tiles"><div class="tile"><b>{k['tested']} / {k['controls']}</b><span>Controls tested</span></div>
<div class="tile"><b style="color:#9a2a14">{k['with_exceptions']}</b><span>Controls with exceptions</span></div>
<div class="tile"><b>{k['exceptions']}</b><span>Exceptions in total</span></div>
<div class="tile"><b>{k['sod_conflicts']}</b><span>Segregation-of-duties conflicts</span></div></div>
{''.join(sections)}
<h2>Segregation-of-duties matrix</h2>{sod_matrix_html(r)}
<p class="legend"><i style="background:#b42318"></i>Users hold both roles<i style="background:#dcebd9"></i>Incompatible pair, no conflicts<i style="background:#f1f3ee"></i>Compatible</p>
<h2>Users with conflicting roles</h2>{conflicts}
<div class="sign"><div>Prepared by / date</div><div>Reviewed by / date</div></div>
<p class="note">{e(DISCLAIMER)}</p></div></main></body></html>"""


WRITERS = {"json": to_json, "csv": to_csv, "md": to_markdown, "html": to_html}
