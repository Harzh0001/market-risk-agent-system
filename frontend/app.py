"""Streamlit human-in-the-loop dashboard for market risk agent."""
import json
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from pipelines.orchestrator import MarketRiskOrchestrator

st.set_page_config(page_title="Agentic Market Risk", layout="wide", initial_sidebar_state="expanded")

# --- UI Aesthetics Customization ---
st.markdown("""
<style>
.metric-box {
    background-color: #1E1E1E;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Agentic Market Risk Monitor")
st.markdown("Multi-agent prediction system aligned with **RBI Guidelines**, **Basel III**, and **SBC2**.")

with st.sidebar:
    st.header("Control Panel")
    ticker = st.text_input("Ticker", value="^NSEI").strip()
    run_date = st.date_input("As of date", value=datetime.today())
    run = st.button("🚀 Run Agentic Workflow", use_container_width=True, type="primary")

if run:
    with st.status("Initializing Agent Crews...", expanded=True) as status:
        st.write("Orchestrator is orchestrating the workflow...")
        
        orch = MarketRiskOrchestrator()
        
        st.write("Executing Ingest, Normalize, Var, Factor, Macro, Compliance, Limit, and Drift agents...")
        trace = orch.run(run_date=run_date.isoformat(), ticker=ticker)
        
        status.update(label="All agents finished successfully!", state="complete", expanded=False)

    st.success("Workflow Execution Complete")
    
    # 1. Visualization
    st.divider()
    st.subheader(f"📈 Historical Performance ({ticker})")
    try:
        df_clean = pd.read_parquet(r"data/silver/market_clean.parquet")
        df_ticker = df_clean[df_clean["ticker"] == ticker]
        if not df_ticker.empty:
            fig = px.line(df_ticker, x="date", y="Close", title=f"Closing Price: {ticker}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available to plot for the selected ticker.")
    except Exception as e:
        st.warning("Could not load historical data for charting.")

    final = trace.get("final_decision_object")
    if final:
        # 2. Key Risk Metrics (VaR and ES)
        st.divider()
        st.subheader("📊 Key Risk Metrics")
        v = final.get("var_breakdown")
        if v:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("1-Day VaR (99%)", f"{v.get('var_1d_99', 0):.2%}")
            col2.metric("10-Day VaR (99%)", f"{v.get('var_10d_99', 0):.2%}")
            col3.metric("1-Day ES (99%)", f"{v.get('es_1d_99', 0):.2%}")
            col4.metric("10-Day ES (99%)", f"{v.get('es_10d_99', 0):.2%}")
        else:
            st.info("No VaR Breakdown available.")

        # 3. Compliance and Governance
        st.divider()
        st.subheader("⚖️ Compliance & Governance")
        
        col_comp, col_gov = st.columns(2)
        
        with col_comp:
            st.markdown("#### Regulatory Flags")
            flags = final.get("compliance_flags", [])
            if flags:
                for f in flags:
                    flag_status = f.get("status", "unknown").lower()
                    title = f"**{f.get('regulation')}**: {f.get('article_or_circular')}"
                    if flag_status == "passed" or flag_status == "pass":
                        st.success(title + " ✅")
                    elif flag_status == "failed" or flag_status == "fail":
                        st.error(title + f" ❌\n\n*Remediation: {f.get('remediation', 'N/A')}*")
                    else:
                        st.warning(title + f" ⚠️ ({flag_status})")
            else:
                st.info("No compliance flags raised.")

        with col_gov:
            st.markdown("#### Final Decision Summary")
            explanation = final.get("explanation", "No explanation provided.")
            st.info(explanation)
            
            st.markdown(f"**Model Version:** `{final.get('model_version')}`")
            st.markdown(f"**Technique:** `{final.get('model_technique')}`")
            st.markdown(f"**Requires Approval:** `{'Yes' if final.get('requires_approval') else 'No'}`")

        # 4. Agent Execution Trace (Expandable)
        st.divider()
        with st.expander("🛠️ View Agent Execution Trace & Data Lineage"):
            st.markdown("### Step-by-Step Execution")
            steps_df = pd.DataFrame(trace.get("steps", []))
            st.dataframe(steps_df, use_container_width=True)
            
            st.markdown("### Data Lineage")
            lineage = final.get("data_lineage", [])
            if lineage:
                st.dataframe(pd.DataFrame(lineage), use_container_width=True)
            else:
                st.write("No lineage data available.")
