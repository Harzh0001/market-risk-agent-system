"""Streamlit human-in-the-loop dashboard for market risk agent."""
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from pipelines.orchestrator import MarketRiskOrchestrator

st.set_page_config(page_title="Agentic Market Risk", layout="wide")
st.title("Agentic Market Risk Monitor — RBI-aligned")
with st.sidebar:
    ticker = st.text_input("Ticker", value="^NSEI")
    run_date = st.date_input("As of date", value=datetime.today())
    run = st.button("Run workflow")
if run:
    with st.spinner("Running crews..."):
        orch = MarketRiskOrchestrator()
        trace = orch.run(run_date=run_date.isoformat(), ticker=ticker)
    st.subheader("Orchestrator trace")
    st.json(trace)
    final = trace.get("final_decision_object")
    if final:
        df = pd.DataFrame([final])
        st.dataframe(df)
        v = final.get("var_breakdown") or {}
        st.subheader("VaR breakdown")
        st.json(v)
