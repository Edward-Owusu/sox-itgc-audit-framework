"""Interactive dashboard for the SOX ITGC Audit Framework.

Run locally:   streamlit run app/streamlit_app.py

Layout: no sidebar. The main screen works like an audit binder: an index of controls on the left with a
result mark beside each, and the workpaper for the selected control on the right.
"""

from __future__ import annotations

import sys
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ui  # noqa: E402
from sox_itgc import __version__, load_engagement, parse_engagement, test_controls  # noqa: E402
from sox_itgc.engine import EXCEPTIONS, FILES, NO_EXCEPTIONS, DataError  # noqa: E402
from sox_itgc.reporting import DISCLAIMER, MATRIX_CSS, sod_matrix_html, to_csv, to_html, to_json, to_markdown  # noqa: E402

S = ROOT / "samples"
SAMPLES = {
    "Manufacturer with control gaps (fictional)": "granite_peak",
    "Distributor with clean results (fictional)": "bluewater",
}
def short(text: str, n: int = 46) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


MARK = {NO_EXCEPTIONS: "✓", EXCEPTIONS: "✕"}
RESULT_COLOR = {NO_EXCEPTIONS: "#166534", EXCEPTIONS: "#B42318"}

PAL = ui.Palette(accent="#166534", band="#14231A", band_text="#FFFFFF", band_sub="#B9CDBD",
                 card="#FFFFFF", line="#DCE5D6", ink="#14231A", muted="#5A6B5E")
ui.setup("SOX IT general controls testing", "ITGC workpapers · access, change, operations · SoD",
         "Test the IT general controls behind financial reporting the way an IT auditor does: access to programs "
         "and data, program change and computer operations, plus a segregation-of-duties matrix.", "📒", PAL)
st.markdown("""<style>
.wp { background:#FFFEF8; border:1px solid #DCE5D6; border-radius:6px; padding:18px 22px;
      box-shadow: 0 1px 0 #DCE5D6, 0 3px 0 -1px #FFFEF8, 0 4px 0 -1px #DCE5D6; }
.wp .ref { font: 700 12px Arial; letter-spacing:.12em; color:#5A6B5E; text-transform:uppercase; }
.wp h3 { font-family: Georgia, serif; margin: 2px 0 10px; padding:0; color:#14231A; }
.wp table { width:100%; border-collapse:collapse; font-size:14px; margin-bottom:10px }
.wp td { border-bottom:1px solid #E8EEE4; padding:6px 4px; vertical-align:top }
.wp td:first-child { width:150px; color:#5A6B5E }
.stamp { display:inline-block; border:3px solid; border-radius:6px; padding:4px 12px; font:800 14px Arial;
         letter-spacing:.1em; text-transform:uppercase; transform:rotate(-3deg); margin-top:6px }
</style>""", unsafe_allow_html=True)

# ---- Top row: data -----------------------------------------------------------------------------------
t1, t2 = st.columns([1.5, 4], vertical_alignment="top")
engagement = None
with t1:
    st.caption("Data")
    source = ui.choose("Data", ["Use a sample", "Upload my own files"], key="source", format_func=ui.source_label)
try:
    if source == "Use a sample":
        with t2:
            st.caption("Sample company")
            engagement = load_engagement(S / SAMPLES[st.selectbox("Sample company", list(SAMPLES),
                                                                  label_visibility="collapsed")])
    else:
        with t2:
            st.caption("Expected: " + ", ".join(f"{n}.csv" for n in FILES))
            ups = st.file_uploader("Upload all seven CSV files", type=["csv"], accept_multiple_files=True,
                                   label_visibility="collapsed")
        e1, e2, e3, e4, e5 = st.columns(5)
        org = e1.text_input("Company", "My company")
        system = e2.text_input("System in scope", "ERP")
        start = e3.date_input("Period start", date(2026, 1, 1))
        end = e4.date_input("Period end", date(2026, 9, 30))
        days = e5.number_input("Days allowed to remove leavers", 0, 30, 3)
        if ups:
            texts = {Path(u.name).stem.lower(): u.getvalue().decode("utf-8-sig", errors="replace") for u in ups}
            engagement = parse_engagement(texts, {"organization": org, "system": system,
                                                  "period_start": start.isoformat(), "period_end": end.isoformat(),
                                                  "termination_removal_days": int(days)})
except DataError as exc:
    st.error(f"The files could not be read. {exc}")

if engagement is None:
    st.info("Upload all seven files above, or switch to a sample, to open the binder.")
    ui.footer("sox_itgc", __version__, "sox-itgc-audit-framework", DISCLAIMER)
    st.stop()

r = test_controls(engagement)
k = r.counts()
st.markdown(f"<div class='g-sec'>{escape(r.organization)}</div>", unsafe_allow_html=True)
st.caption(f"{r.system} · period {r.period_start} to {r.period_end}")
ui.tiles([(f"{k['tested']} of {k['controls']}", "Controls tested"),
          (k["with_exceptions"], "Controls with exceptions", "#B42318"),
          (k["exceptions"], "Exceptions in total", "#B45309"),
          (k["sod_conflicts"], "Segregation-of-duties conflicts", "#7C2D12")], PAL)

view = ui.choose("View", ["Workpapers", "Summary of results", "Segregation of duties"], key="view")
domains = r.by_domain()

if view == "Workpapers":
    idx, paper = st.columns([1, 2.4], gap="large")
    with idx:
        ui.section("Binder index", "✓ no exceptions · ✕ exceptions noted · – no population")
        refs = [c.id for c in r.controls]
        names = {c.id: c for c in r.controls}
        pick = st.radio("Control", refs, label_visibility="collapsed",
                        format_func=lambda i: f"{MARK.get(names[i].result, '–')}  {i} · {short(names[i].objective)}")
    c = names[pick]
    with paper:
        color = RESULT_COLOR.get(c.result, "#64748B")
        rows = (f"<tr><td>Domain</td><td>{escape(c.domain_name)}</td></tr>"
                f"<tr><td>Test performed</td><td>{escape(c.procedure)}</td></tr>"
                f"<tr><td>Population</td><td>{c.population} item(s)</td></tr>"
                f"<tr><td>Exceptions</td><td>{len(c.exceptions)} ({c.exception_rate:.0f}%)</td></tr>"
                f"<tr><td>NIST SP 800-53</td><td>{escape(', '.join(c.nist))}</td></tr>")
        st.markdown(f"<div class='wp'><div class='ref'>Workpaper {escape(c.id)} · {escape(r.system)} · "
                    f"{escape(r.period_start)} to {escape(r.period_end)}</div><h3>{escape(c.objective)}</h3>"
                    f"<table>{rows}</table><span class='stamp' style='color:{color};border-color:{color}'>"
                    f"{escape(c.result)}</span></div>", unsafe_allow_html=True)
        if c.exceptions:
            ui.section(f"Exceptions ({len(c.exceptions)})")
            st.dataframe(pd.DataFrame([{"Item": x.item, "Exception": x.detail} for x in c.exceptions]),
                         hide_index=True, use_container_width=True)

elif view == "Summary of results":
    cols = st.columns(len(domains))
    for col, (domain, controls) in zip(cols, domains.items()):
        with col:
            bad = sum(1 for x in controls if x.result == EXCEPTIONS)
            ui.section(controls[0].domain_name if controls else domain,
                       f"{len(controls) - bad} of {len(controls)} without exceptions")
            for x in controls:
                colr = RESULT_COLOR.get(x.result, "#64748B")
                ui.card(f"<div class='h'>{ui.pill(MARK.get(x.result, '–') + ' ' + x.result, colr)}"
                        f"{escape(x.id)}</div>",
                        f"<div class='d'>{escape(x.objective)}</div><div class='s'>Population {x.population} · "
                        f"exceptions {len(x.exceptions)} · {escape(', '.join(x.nist))}</div>", accent=colr)

else:
    ui.section("Segregation of duties", "Each cell pairs two roles. Red cells show how many active users hold an "
               "incompatible pair; green cells are incompatible pairs with no conflicts; grey pairs are compatible.")
    st.markdown(f"<style>{MATRIX_CSS}</style><div style='overflow-x:auto;background:#fff;border:1px solid #DCE5D6;"
                f"border-radius:12px;padding:14px'>{sod_matrix_html(r)}</div>", unsafe_allow_html=True)
    if r.sod_conflicts:
        st.dataframe(pd.DataFrame([{"User": x["user"], "Name": x["name"], "Department": x["department"],
                                    "Conflicting roles": " + ".join(x["roles"]), "Risk": x["risk"]}
                                   for x in r.sod_conflicts]), hide_index=True, use_container_width=True)
    else:
        st.success("No users hold incompatible roles.")

ui.downloads([("HTML worksheet", to_html(r), "itgc_worksheet.html", "text/html"),
              ("Markdown", to_markdown(r), "itgc_worksheet.md", "text/markdown"),
              ("CSV (one row per exception)", to_csv(r), "itgc_exceptions.csv", "text/csv"),
              ("JSON results", to_json(r), "itgc_results.json", "application/json")])
ui.footer("sox_itgc", __version__, "sox-itgc-audit-framework", DISCLAIMER)
