"""Diabetes care-gaps dashboard (Streamlit). Every number comes from the governed semantic model
(dcg/models/semantic/dcg_semantic_model.yml) through the same metric engine the AI agent uses,
with small-cell suppression applied.

Run: make dashboard   (or: streamlit run app/dashboard.py)
"""
import os
import sys
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dcg" / "scripts"))
from run_pipeline import MET, query_metric  # noqa: E402

DB = os.environ.get("DCG_DUCKDB", str(ROOT / "data" / "dcg.duckdb"))
VARS = yaml.safe_load(open(ROOT / "dcg" / "dbt_project.yml"))["vars"]
MIN_CELL = int(VARS.get("min_cell_size", 5))
GAPS = ["a1c_test", "a1c_control", "bp_control", "kidney_screen", "lipid_test", "eye_exam", "foot_exam", "statin", "cardiorenal"]
HEADLINE = ["a1c_tested_12m_rate", "a1c_at_target_rate", "bp_at_target_rate", "kidney_screened_rate",
            "lipid_tested_rate", "eye_exam_rate", "foot_exam_rate", "statin_rate_40plus", "all_four_tests_rate", "any_gap_rate"]
DIMS = {"(none)": None, "Age band": "age_band", "Sex": "sex", "Province": "province", "Diabetes type": "diabetes_type",
        "Therapy profile": "therapy_profile", "Any complication": "has_any_complication",
        "Case basis": "case_basis", "CKD or ASCVD": "has_ckd_or_ascvd"}

st.set_page_config(page_title="Diabetes Care Gaps — HAC PoC", layout="wide")


@st.cache_resource
def connect():
    if not Path(DB).exists():
        st.error(f"No database at {DB}. Run `make pipeline` (or `make offline`) first.")
        st.stop()
    return duckdb.connect(DB, read_only=True)


con = connect()


def q(metric, group_by=()):
    return query_metric(con, metric, group_by=tuple(group_by), min_cell=MIN_CELL)


def fmt(cell, pct=True):
    if cell is None or cell.get("suppressed") or cell.get("value") is None:
        return "suppressed (<5)" if cell and cell.get("suppressed") else "—"
    return f"{cell['value']:.1%}" if pct else f"{cell['value']:,.0f}"


meta = con.execute("select max(period_end), max(data_source), max(phenotype_id), max(phenotype_version), max(map_version) from fct_diabetes_patient_period").fetchone()
st.title("Diabetes care gaps")
st.caption(f"Period ending **{meta[0]}** · data source **{meta[1]}** · cells under {MIN_CELL} suppressed · "
           f"definitions: Diabetes Canada CPG-based parameters (A1C ≤ {VARS['a1c_target_pct']}%, BP < "
           f"{VARS['bp_sys_target']}/{VARS['bp_dia_target']}) · cohort **{meta[2]} v{meta[3]}** · terminology map **{meta[4]}**")
if meta[1] == "synthetic":
    st.warning("Synthetic data (Synthea) — not real-world prevalence or performance.")

# ── Headline tiles ─────────────────────────────────────────────────────────
tiles = ["cohort_size", "a1c_tested_12m_rate", "a1c_at_target_rate", "bp_at_target_rate", "any_gap_rate"]
for col, m in zip(st.columns(len(tiles)), tiles):
    cell = q(m).get((), None)
    col.metric(MET[m]["label"], fmt(cell, pct=m != "cohort_size"))

# ── Gaps by dimension ──────────────────────────────────────────────────────
st.subheader("Where the gaps are")
dim_label = st.selectbox("Break down by", list(DIMS), index=1)
dim = DIMS[dim_label]
rows = []
for g in GAPS:
    for key, cell in q(f"gap_{g}_rate", [dim] if dim else []).items():
        rows.append({"gap": MET[f"gap_{g}_rate"]["label"].replace("Gap: ", ""), "group": key[0] if key else "All",
                     "rate": None if cell.get("suppressed") else cell["value"], "suppressed": cell.get("suppressed")})
df = pd.DataFrame(rows)
chart = alt.Chart(df.dropna(subset=["rate"])).mark_bar().encode(
    y=alt.Y("gap:N", title=None, sort=[MET[f"gap_{g}_rate"]["label"].replace("Gap: ", "") for g in GAPS]),
    x=alt.X("rate:Q", title="Share of cohort with the gap open", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
    color=alt.Color("group:N", title=dim_label if dim else None),
    yOffset="group:N" if dim else alt.value(0),
    tooltip=["gap", "group", alt.Tooltip("rate:Q", format=".1%")],
).properties(height=360)
st.altair_chart(chart, width="stretch")
if df["suppressed"].any():
    st.caption(f"{int(df['suppressed'].sum())} cells suppressed (fewer than {MIN_CELL} people).")
st.caption("Foot exam: Synthea does not generate diabetic foot exams, so this gap is 100% on synthetic data by construction.")

# ── Indicator table ────────────────────────────────────────────────────────
st.subheader("Indicators")
table = []
for m in HEADLINE:
    cell = q(m).get((), {})
    meta_m = MET[m]["config"]["meta"]
    table.append({"Indicator": MET[m]["label"], "Value": fmt(cell),
                  "Numerator / denominator": "—" if cell.get("suppressed") else f"{cell.get('numerator', '')} / {cell.get('denominator', '')}",
                  "Definition": MET[m]["description"], "Caveats": " ".join(meta_m.get("caveats", []))})
st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")

# ── DCI measure set ────────────────────────────────────────────────────────
st.subheader("DCI measure set (M2–M10)")
dci = [("M2", "a1c_tested_12m_rate"), ("M3", "a1c_at_target_rate"), ("M4", "a1c_poor_control_tested_rate"), ("M5", "kidney_screened_rate"),
       ("M6", "bp_at_target_measured_rate"), ("M7", "statin_rate_40plus"), ("M8", "eye_exam_rate"), ("M9", "cardiorenal_agent_rate")]
drows = [{"ID": i, "Measure": MET[m]["label"], "Value": fmt(q(m).get((), None))} for i, m in dci]
acute = q("acute_dm_admissions_per_1000").get((), None)
drows.append({"ID": "M10", "Measure": MET["acute_dm_admissions_per_1000"]["label"],
              "Value": "—" if not acute or acute.get("value") is None else f"{acute['value']:.1f}"})
st.dataframe(pd.DataFrame(drows), hide_index=True, width="stretch")
cb = {k[0]: c for k, c in q("cohort_size", ["case_basis"]).items()}
st.caption("Who is in the cohort, by qualifying evidence: " + " · ".join(
    f"{k.replace('_', ' ')} {'suppressed' if c.get('suppressed') else int(c['value'])}" for k, c in sorted(cb.items()))
    + ". Diabetes type is a heuristic. M11 (equity stratification) needs the restricted equity role.")

# ── Cohort profile ─────────────────────────────────────────────────────────
st.subheader("Cohort profile")
st.caption("Levels are context: a median BP or BMI does not show control, so each sits beside its rate.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Median latest A1C", (lambda c: "—" if not c or c.get("value") is None else f"{c['value']:.1f}%")(
          q("a1c_latest_median_pct").get((), None)), help=f"At target: {fmt(q('a1c_at_target_rate').get((), None))}")
c2.metric("Median latest BP", (lambda a, b: "—" if not a or a.get("value") is None else f"{a['value']:.0f}/{b['value']:.0f} mmHg")(
          q("bp_systolic_median_mmhg").get((), None), q("bp_diastolic_median_mmhg").get((), None)),
          help=f"At target (<{VARS['bp_sys_target']}/{VARS['bp_dia_target']}): {fmt(q('bp_at_target_rate').get((), None))}")
c3.metric("Median latest BMI", (lambda c: "—" if not c or c.get("value") is None else f"{c['value']:.1f} kg/m²")(
          q("bmi_latest_median_kg_m2").get((), None)), help=f"BMI recorded in 12 months: {fmt(q('bmi_recorded_rate').get((), None))}")
c4.metric(MET["complication_rate"]["label"], fmt(q("complication_rate").get((), None)))

left, right = st.columns(2)
with left:
    meds = ["antihyperglycemic", "metformin", "insulin", "sglt2i", "glp1ra", "dpp4i", "sulfonylurea", "tzd", "acei_arb"]
    mrows = [{"Medication class": MET[f"{k}_rate"]["label"].replace(" use", ""), "Share of cohort": fmt(q(f"{k}_rate").get((), None))} for k in meds]
    mrows.append({"Medication class": "Statin (age 40+)", "Share of cohort": fmt(q("statin_rate_40plus").get((), None))})
    st.dataframe(pd.DataFrame(mrows), hide_index=True, width="stretch")
    st.caption("Order or pharmacy dispense in the last 12 months, or an active order, by ATC class.")
with right:
    bmi = [{"BMI category": k[0], "People": None if c.get("suppressed") else c["value"]}
           for k, c in sorted(q("cohort_size", ["bmi_category"]).items())]
    bdf = pd.DataFrame(bmi)
    if not bdf.empty and bdf["People"].notna().any():
        st.altair_chart(alt.Chart(bdf.dropna()).mark_bar().encode(
            x=alt.X("People:Q"), y=alt.Y("BMI category:N", title=None,
            sort=["underweight (<18.5)", "normal (18.5-24.9)", "overweight (25-29.9)", "obese (30+)", "not recorded"])).properties(height=180),
            width="stretch")
    else:
        st.caption("BMI categories: all cells suppressed (fewer than 5 people).")

# ── Data quality ───────────────────────────────────────────────────────────
with st.expander("Data quality (AI-ready data checks)"):
    dq = [{"Check": MET[m]["label"].replace("DQ: ", ""), "Share of cohort affected": fmt(q(m).get((), None))}
          for m in MET if m.startswith("dq_")]
    st.dataframe(pd.DataFrame(dq), hide_index=True, width="stretch")
