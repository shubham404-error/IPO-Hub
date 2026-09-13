import streamlit as st
import pandas as pd
from pathlib import Path

from config import DB_PATH
from collector import collect_once
from database import Database, get_df
from styles import inject_styles
from formatters import format_date, normalized_status

st.set_page_config(
    page_title="IPO Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

inject_styles()

if "ai_scores" not in st.session_state:
    st.session_state["ai_scores"] = {}
if "ai_chat_messages" not in st.session_state:
    st.session_state["ai_chat_messages"] = []

if not Path(DB_PATH).exists():
    with st.sidebar:
        st.markdown("# IPO Intelligence")
        st.caption("Research, demand, and AI decision support")
        st.markdown("---")
        if st.button("Refresh data", use_container_width=True):
            try:
                with st.spinner("Refreshing IPO data..."):
                    result = collect_once(enrich=True)
                st.success(f"Updated {result['count']} IPOs.")
                st.rerun()
            except Exception as exc:
                st.error(f"Collector error: {exc}")
        st.caption("Data is refreshed from the configured IPO sources.")
    st.title("IPO Intelligence")
    st.info("No IPO data yet. Use Refresh data in the sidebar.")
    st.stop()

try:
    df = get_df()
except Exception as exc:
    st.error(f"Database error: {exc}")
    st.stop()

if df.empty:
    with st.sidebar:
        st.markdown("# IPO Intelligence")
        st.caption("Research, demand, and AI decision support")
        st.markdown("---")
        if st.button("Refresh data", use_container_width=True):
            try:
                with st.spinner("Refreshing IPO data..."):
                    result = collect_once(enrich=True)
                st.success(f"Updated {result['count']} IPOs.")
                st.rerun()
            except Exception as exc:
                st.error(f"Collector error: {exc}")
        st.caption("Data is refreshed from the configured IPO sources.")
    st.title("IPO Intelligence")
    st.info("No IPOs collected yet. Use Refresh data in the sidebar.")
    st.stop()

df["display_status"] = df.apply(normalized_status, axis=1)

from pages.discovery import discovery_page
from pages.allotment import allotment_page
from pages.ai_analyst import ai_analyst_page
from pages.ipo_detail import ipo_detail_page
from pages.guide import guide_page

DISCOVERY_PAGE = st.Page(
    lambda: discovery_page(df),
    title="Discovery",
    icon="🔎",
    url_path="discovery",
    default=True,
)
ALLOTMENT_PAGE = st.Page(
    lambda: allotment_page(df),
    title="Allotment Optimizer",
    icon="🎯",
    url_path="allotment-chances",
)
AI_ANALYST_PAGE = st.Page(
    lambda: ai_analyst_page(df),
    title="AI Analyst",
    icon="🤖",
    url_path="ai-analyst",
)
IPO_DETAIL_PAGE = st.Page(
    lambda: ipo_detail_page(df),
    title="IPO Detail",
    icon="📄",
    url_path="ipo-detail",
    visibility="hidden",
)
GUIDE_PAGE = st.Page(
    lambda: guide_page(),
    title="User Guide",
    icon="📖",
    url_path="guide",
)

pages = [
    DISCOVERY_PAGE,
    ALLOTMENT_PAGE,
    AI_ANALYST_PAGE,
    IPO_DETAIL_PAGE,
    GUIDE_PAGE,
]

pg = st.navigation(pages, position="hidden")

with st.sidebar:
    st.markdown("# IPO Intelligence")
    st.caption("Research, demand, and AI decision support")
    st.markdown("### Navigation")
    st.page_link(DISCOVERY_PAGE, label="Discovery", icon="🔎")
    st.page_link(ALLOTMENT_PAGE, label="Allotment Optimizer", icon="🎯")
    st.page_link(AI_ANALYST_PAGE, label="AI Analyst", icon="🤖")
    st.page_link(GUIDE_PAGE, label="User Guide", icon="📖")
    st.markdown("---")
    if st.button("Refresh data", use_container_width=True):
        try:
            with st.spinner("Refreshing IPO data..."):
                result = collect_once(enrich=True)
            st.success(f"Updated {result['count']} IPOs.")
            st.rerun()
        except Exception as exc:
            st.error(f"Collector error: {exc}")
    try:
        latest = df["collected_at"].dropna().max()
        if pd.notna(latest):
            st.caption(f"Last refresh: {format_date(latest, with_time=True)}")
        else:
            st.caption("Data is refreshed from the configured IPO sources.")
    except Exception:
        st.caption("Data is refreshed from the configured IPO sources.")

pg.run()
