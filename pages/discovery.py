import json
from textwrap import dedent
import streamlit as st
import pandas as pd

from formatters import clean_text, normalized_status, format_date, is_missing, price_band, money, multiple, score_color
from database import Database
from ai_advisor import build_ai_dataset, hash_dataset, ai_score_for_ipo
from pages.ipo_detail import render_ai_score

def get_summary(l, i, a):
    ls = "Strong listing setup" if l >= 75 else ("Moderate listing setup" if l >= 50 else "Weak listing setup")
    iv = "Strong fundamentals" if i >= 75 else ("Moderate fundamentals" if i >= 50 else "Weak fundamentals")
    al = "High retail allotment opportunity" if a >= 75 else ("Moderate retail allotment opportunity" if a >= 50 else "Low retail allotment opportunity")
    return f"{ls} • {iv} • {al}"

def render_section(title, section_df):
    if section_df.empty:
        return

    st.markdown(f"### {title}")

    for _, row in section_df.iterrows():
        source_id = str(row["source_id"])
        company = clean_text(row.get("company_name")) or "Unknown IPO"
        status = normalized_status(row)
        segment_name = clean_text(row.get("segment")) or "IPO"
        score = st.session_state["ai_scores"].get(source_id)
        
        # Pre-load cached AI score if available and not yet in session
        if not score:
            dataset = build_ai_dataset(pd.DataFrame([row]))
            data_hash = hash_dataset(dataset)
            db = Database()
            try:
                cached = db.get_ai_verdict(source_id)
                if cached and cached["data_hash"] == data_hash:
                    score = json.loads(cached["recommendation_json"])
                    st.session_state["ai_scores"][source_id] = score
            finally:
                db.close()

        close_open_line = ""
        if status == "Live":
            close_open_line = f'<div class="ipo-card-meta">Closes {format_date(row.get("close_date"))}</div>'
        elif status == "Upcoming":
            close_open_line = f'<div class="ipo-card-meta">Opens {format_date(row.get("open_date"))}</div>'

        lot_value = (
            f'{int(row["lot_size"]):,}'
            if not is_missing(row.get("lot_size"))
            else "—"
        )

        with st.container(border=True):
            card_html = dedent(f'''<div class="ipo-card-content">
                <div class="ipo-card-title">{company}</div>
                <div class="ipo-card-meta">{segment_name} · {status}</div>
                {close_open_line}
                <div class="ipo-metric-grid">
                    <div class="ipo-metric">
                        <div class="ipo-card-label">Price band</div>
                        <div class="ipo-card-value">{price_band(row)}</div>
                    </div>
                    <div class="ipo-metric">
                        <div class="ipo-card-label">Lot size</div>
                        <div class="ipo-card-value">{lot_value}</div>
                    </div>
                    <div class="ipo-metric">
                        <div class="ipo-card-label">GMP</div>
                        <div class="ipo-card-value">{money(row.get("gmp"))}</div>
                    </div>
                    <div class="ipo-metric">
                        <div class="ipo-card-label">Subscription</div>
                        <div class="ipo-card-value">{multiple(row.get("subscription"))}</div>
                    </div>
                </div>
            </div>''').strip()
            st.html(card_html)
            
            db = Database()
            try:
                signals = db.get_signal(source_id)
            finally:
                db.close()
            
            if signals:
                listing_score = signals.get('listing_score', 0)
                inv_score = signals.get('investment_score', 0)
                allot_score = signals.get('allotment_score', 0)
                    
                st.markdown(f"**Listing:** {score_color(listing_score)} {listing_score} | "
                            f"**Investment:** {score_color(inv_score)} {inv_score} | "
                            f"**Allotment:** {score_color(allot_score)} {allot_score}")
                st.caption(get_summary(listing_score, inv_score, allot_score))
            
            # Check for staleness
            last_updated = row.get("subscription_updated_at") or row.get("collected_at")
            if last_updated:
                st.caption(f"Data updated: {format_date(last_updated, with_time=True)}")

            if not score and st.button("Ask AI", key=f"ask_ai_{source_id}", use_container_width=True):
                ai_score_for_ipo(row)
                st.rerun()
            elif score:
                # In shadow mode, we keep calling the old render_ai_score
                render_ai_score(score)

            if st.button("View IPO", key=f"view_{source_id}", use_container_width=True):
                st.session_state["selected_ipo"] = source_id
                st.switch_page("ipo-detail")

            if score:
                st.markdown('<div class="ai-score-strip">', unsafe_allow_html=True)
                render_ai_score(score)
                risks = score.get("key_risks", [])
                if risks:
                    st.caption("Risks: " + " · ".join(risks[:3]))
                st.markdown("</div>", unsafe_allow_html=True)


def discovery_page(df):
    st.title("IPO Discovery")
    st.caption("Find open and upcoming IPOs, then use Ask AI for a quick evidence-based decision view.")

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    with c1:
        segment = st.selectbox("Segment", ["All", "Mainboard", "SME"])
    with c2:
        status_filter = st.selectbox("Status", ["All", "Live", "Upcoming", "Closed"])
    with c3:
        # Changed options to explicitly match Date, GMP, Issue Size per request
        sort = st.selectbox("Sort", ["Date", "GMP", "Issue Size"])
    with c4:
        search = st.text_input("Search IPO", placeholder="Company name...")

    view = df.copy()
    if segment != "All":
        view = view[view["segment"].fillna("").str.contains(segment, case=False, na=False)]
    if status_filter != "All":
        view = view[view["display_status"] == status_filter]
    if search:
        view = view[view["company_name"].fillna("").str.contains(search, case=False, na=False)]

    if sort == "Issue Size":
        view["sort_issue"] = pd.to_numeric(view["issue_size"], errors="coerce")
        view = view.sort_values("sort_issue", ascending=False, na_position="last")
    elif sort == "GMP":
        view = view.sort_values("gmp_pct", ascending=False, na_position="last")
    else:
        # Date sorting
        view["sort_close"] = pd.to_datetime(view["close_date"], errors="coerce")
        view = view.sort_values(["sort_close", "company_name"], na_position="last")

    live_count = int((df["display_status"] == "Live").sum())
    upcoming_count = int((df["display_status"] == "Upcoming").sum())
    closed_count = int(df["display_status"].isin(["Closed", "Allotment Out", "Allotment Awaited"]).sum())

    a, b = st.columns(2)
    a.metric("IPOs tracked", len(df))
    b.metric("Open now", live_count)
    c, d = st.columns(2)
    c.metric("Upcoming", upcoming_count)
    d.metric("Closed / allotment", closed_count)

    render_section("Open now", view[view["display_status"] == "Live"])
    render_section("Upcoming", view[view["display_status"] == "Upcoming"])
    render_section("Closed / allotment", view[view["display_status"].isin(["Closed", "Allotment Out", "Allotment Awaited"])])

    if view.empty:
        st.info("No IPOs match your filters.")
