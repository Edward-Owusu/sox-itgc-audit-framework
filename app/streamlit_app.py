"""Interactive dashboard for the SOX ITGC Audit Framework.

Run locally:   streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sox_itgc import __version__, load_engagement, parse_engagement, test_controls  # noqa: E402
from sox_itgc.engine import EXCEPTIONS, FILES, NO_EXCEPTIONS, DataError  # noqa: E402
from sox_itgc.reporting import DISCLAIMER, MATRIX_CSS, sod_matrix_html, to_csv, to_html, to_json, to_markdown  # noqa: E402

S = ROOT / "samples"
SAMPLES = {
    "Manufacturer with control gaps (fictional)": "granite_peak",
    "Distributor with clean results (fictional)": "bluewater",
}
ICON = {NO_EXCEPTIONS: "✅", EXCEPTIONS: "⚠️"}

st.set_page_config(page_title="SOX ITGC Audit Framework", page_icon="📒", layout="wide")
st.title("📒 SOX IT general controls testing")
st.write("Test the IT general controls behind a company's financial reporting the way an IT auditor does: access to "
         "programs and data, program change, and computer operations, plus a segregation-of-duties matrix. Built for "
         "smaller public companies, pre-IPO businesses, and the auditors who test them.")

with st.sidebar:
    st.header("1. Choose data")
    source = st.radio("Data", ["Use a sample", "Upload my own files"], label_visibility="collapsed")
    engagement = None
    try:
        if source == "Use a sample":
            engagement = load_engagement(S / SAMPLES[st.selectbox("Sample company", list(SAMPLES))])
        else:
            ups = st.file_uploader("Upload all seven CSV files", type=["csv"], accept_multiple_files=True)
            st.caption("Expected: " + ", ".join(f"{n}.csv" for n in FILES))
            org = st.text_input("Company", "My company")
            system = st.text_input("System in scope", "ERP")
            p1, p2 = st.columns(2)
            start = p1.date_input("Period start", date(2026, 1, 1))
            end = p2.date_input("Period end", date(2026, 9, 30))
            days = st.number_input("Days allowed to remove leavers", 0, 30, 3)
            if ups:
                texts = {Path(u.name).stem.lower(): u.getvalue().decode("utf-8-sig", errors="replace") for u in ups}
                engagement = parse_engagement(texts, {"organization": org, "system": system,
                                                      "period_start": start.isoformat(), "period_end": end.isoformat(),
                                                      "termination_removal_days": int(days)})
    except DataError as exc:
        st.error(f"The files could not be read. {exc}")
    st.caption(f"sox_itgc {__version__}. Runs entirely in this session; files are not stored.")

if engagement is None:
    st.info("Upload all seven files in the sidebar, or switch to a sample, to see the worksheet.")
    st.stop()

r = test_controls(engagement)
k = r.counts()
st.subheader(r.organization)
st.caption(f"{r.system} · period {r.period_start} to {r.period_end}")
m = st.columns(4)
m[0].metric("Controls tested", f"{k['tested']} of {k['controls']}")
m[1].metric("Controls with exceptions", k["with_exceptions"])
m[2].metric("Exceptions in total", k["exceptions"])
m[3].metric("Segregation-of-duties conflicts", k["sod_conflicts"])

tabs = st.tabs(list(r.by_domain()) + ["Segregation of duties"])
for tab, (domain, controls) in zip(tabs, r.by_domain().items()):
    with tab:
        st.dataframe(pd.DataFrame([{"Ref": c.id, "Control objective": c.objective, "Population": c.population,
                                    "Exceptions": len(c.exceptions), "Exception rate": f"{c.exception_rate:.0f}%",
                                    "Result": f"{ICON.get(c.result, '➖')} {c.result}", "NIST 800-53": ", ".join(c.nist)}
                                   for c in controls]), hide_index=True)
        for c in controls:
            with st.expander(f"{ICON.get(c.result, '➖')} {c.id} · {c.objective}"):
                st.markdown(f"**Test performed:** {c.procedure}  \n**Population:** {c.population} · "
                            f"**Exceptions:** {len(c.exceptions)}")
                if c.exceptions:
                    st.dataframe(pd.DataFrame([{"Item": x.item, "Exception": x.detail} for x in c.exceptions]),
                                 hide_index=True)
                else:
                    st.success("No exceptions noted.")
with tabs[-1]:
    st.markdown("Each cell pairs two roles. **Red** cells show how many active users hold an incompatible pair; "
                "**green** cells are incompatible pairs with no conflicts; grey pairs are compatible.")
    st.markdown(f"<style>{MATRIX_CSS}</style><div style='overflow-x:auto'>{sod_matrix_html(r)}</div>",
                unsafe_allow_html=True)
    if r.sod_conflicts:
        st.dataframe(pd.DataFrame([{"User": x["user"], "Name": x["name"], "Department": x["department"],
                                    "Conflicting roles": " + ".join(x["roles"]), "Risk": x["risk"]}
                                   for x in r.sod_conflicts]), hide_index=True)
    else:
        st.success("No users hold incompatible roles.")

st.markdown("### Download the worksheet")
d = st.columns(4)
d[0].download_button("HTML worksheet", to_html(r), "itgc_worksheet.html", "text/html")
d[1].download_button("Markdown", to_markdown(r), "itgc_worksheet.md", "text/markdown")
d[2].download_button("CSV (one row per exception)", to_csv(r), "itgc_exceptions.csv", "text/csv")
d[3].download_button("JSON results", to_json(r), "itgc_results.json", "application/json")
st.caption(DISCLAIMER)
