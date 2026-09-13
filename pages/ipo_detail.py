import pandas as pd
import streamlit as st

from formatters import clean_text, normalized_status, format_date, is_missing, price_band, money, multiple, applications
from database import Database, get_selected_ipo

def render_ai_score(score):
    if not score:
        return
    verdict = score.get("verdict", "Insufficient data")
    investment = score.get("investment_score")
    allotment = score.get("allotment_score")
    confidence = score.get("confidence", "Low")
    st.markdown(f"**AI view: {verdict}** · {confidence} confidence")
    s1, s2 = st.columns(2)
    with s1:
        st.metric("AI Investment", f"{investment}/100" if investment is not None else "—")
    with s2:
        st.metric("AI Allotment", f"{allotment}/100" if allotment is not None else "—")
    reason = clean_text(score.get("reason"))
    if reason:
        st.caption(reason)

def render_ai_verdict_v2(score, base_listing, base_inv, base_allot):
    if not score:
        return
    adj = score.get("ai_adjustment", 0)
    
    st.markdown(f"**CapitalSense Score:** {base_inv + adj}")
    st.caption(f"(Deterministic Base: {base_inv} | AI Qualitative Adjustment: {adj})")
    
    reason = clean_text(score.get("reason"))
    if reason:
        st.caption(f"*AI reasoning:* {reason}")

    sig1, sig2 = st.columns(2)
    with sig1:
        anchor_signal = clean_text(score.get("anchor_signal"))
        if anchor_signal:
            st.markdown(f"**Anchor signal:** {anchor_signal}")
        valuation_signal = clean_text(score.get("valuation_signal"))
        if valuation_signal:
            st.caption(f"Valuation: {valuation_signal}")
    with sig2:
        financial_signal = clean_text(score.get("financial_signal"))
        if financial_signal:
            st.markdown(f"**Financial quality:** {financial_signal}")
        demand_signal = clean_text(score.get("demand_signal"))
        if demand_signal:
            st.caption(f"Demand: {demand_signal}")

    research_notes = clean_text(score.get("research_notes"))
    if research_notes:
        st.caption("Research: " + research_notes)

def ipo_detail_page(df):
    selected_id = st.session_state.get("selected_ipo")
    if not selected_id:
        st.info("Select an IPO from Discovery to view its details.")
        return

    row, sub_history, gmp_history = get_selected_ipo(selected_id)
    if not row:
        st.error("The selected IPO could not be found.")
        if st.button("← Back to Discovery", use_container_width=True):
            st.session_state.pop("selected_ipo", None)
            st.switch_page("discovery")
        return

    if st.button("← Back to Discovery", use_container_width=True):
        st.session_state.pop("selected_ipo", None)
        st.switch_page("discovery")

    st.markdown("---")
    st.title(clean_text(row.get("company_name")) or "IPO")
    status = normalized_status(row)
    st.caption(f"{status} · {clean_text(row.get('segment')) or 'IPO'}")
    
    db = Database()
    try:
        signals = db.get_signal(selected_id)
    finally:
        db.close()
        
    if signals:
        def format_score(score):
            if score >= 75: return f"🟢 STRONG · {score}/100"
            if score >= 50: return f"🟡 SELECTIVE · {score}/100"
            return f"🔴 LOW · {score}/100"
            
        st.markdown("### IPO Signal Snapshot")
        st.markdown(f"**LISTING TRADE**<br/>{format_score(signals.get('listing_score', 0))}", unsafe_allow_html=True)
        st.markdown(f"**LONG-TERM**<br/>{format_score(signals.get('investment_score', 0))}", unsafe_allow_html=True)
        st.markdown(f"**ALLOTMENT**<br/>{format_score(signals.get('allotment_score', 0))}", unsafe_allow_html=True)
        
        velocity = signals.get('subscription_velocity_total', 0)
        nii_velocity = signals.get('subscription_velocity_nii', 0)
        momentum = signals.get('gmp_momentum_24h')
        
        reasons = []
        if momentum is not None:
            if momentum > 0: reasons.append(f"🟢 GMP is improving (+{momentum:.1f}% over 24h)")
            elif momentum < 0: reasons.append(f"🔴 GMP is falling ({momentum:.1f}% over 24h)")
        
        if nii_velocity > 0: reasons.append(f"🟢 NII demand is accelerating (+{nii_velocity:.1f}x/hr)")
        elif velocity > 0: reasons.append(f"🟢 Total demand is accelerating (+{velocity:.1f}x/hr)")
        
        retail = row.get("retail")
        if retail and float(retail) > 10:
            reasons.append(f"🔴 Retail demand is massive ({retail}x), limiting allotment chance.")
            
        pe = row.get("pe_post") or row.get("pe_pre")
        if pe and float(pe) > 40:
            reasons.append(f"🔴 Valuation P/E is stretched at {pe}x.")
        
        if reasons:
            st.markdown("#### What is driving the signal?")
            for r in reasons:
                st.markdown(f"- {r}")
                
        confidence = signals.get("signal_confidence", "Unknown")
        st.markdown(f"**Signal confidence:** {confidence}")
        st.markdown("---")
        
    # Phase 2: Trendlyne Widget Quarantine Testing
    if st.query_params.get("widgets") == "true":
        with st.expander("Trendlyne Consensus", expanded=False):
            st.caption("Note: This external consensus is provided for reference only. CapitalSense AI does not have access to this Trendlyne widget and does not factor it into its analysis.")
            
            # Placeholder widget embed string based on Trendlyne's standard widget frame
            import streamlit.components.v1 as components
            company_name_safe = str(row.get("company_name", "")).lower().replace(" ", "-")
            embed_string = f'''
            <iframe 
                src="https://trendlyne.com/web-widget/ipo/{company_name_safe}/" 
                width="100%" 
                height="100%" 
                frameborder="0" 
                style="border:0;" 
                allowfullscreen>
            </iframe>
            '''
            components.html(embed_string, height=500, scrolling=True)

    m1, m2 = st.columns(2)
    m1.metric("Price band", price_band(row))
    m2.metric("Lot size", f'{int(row["lot_size"]):,}' if not is_missing(row.get("lot_size")) else "—")
    m3, m4 = st.columns(2)
    m3.metric("Issue size", f'₹{float(row["issue_size"]):,.2f} Cr' if not is_missing(row.get("issue_size")) else "—")
    m4.metric("GMP", money(row.get("gmp")))

    st.subheader("IPO timeline")
    t1, t2 = st.columns(2)
    t1.metric("Open", format_date(row.get("open_date")))
    t2.metric("Close", format_date(row.get("close_date")))
    t3, t4 = st.columns(2)
    t3.metric("Allotment", format_date(row.get("allotment_date")))
    t4.metric("Listing", format_date(row.get("listing_date")))

    st.markdown("---")
    st.subheader("Subscription")
    s1, s2 = st.columns(2)
    s1.metric("QIB", multiple(row.get("qib")))
    s2.metric("NII", multiple(row.get("nii")))
    s3, s4 = st.columns(2)
    s3.metric("sNII", multiple(row.get("snii")))
    s4.metric("bNII", multiple(row.get("bnii")))
    s5, s6 = st.columns(2)
    s5.metric("Retail", multiple(row.get("retail")))
    s6.metric("Total", multiple(row.get("subscription")))

    s7, s8 = st.columns(2)
    s7.metric("Applications", applications(row.get("applications")))
    s8.metric("GMP %", f'{float(row["gmp_pct"]):.1f}%' if not is_missing(row.get("gmp_pct")) else "—")

    if sub_history:
        sub_df = pd.DataFrame(sub_history)
        sub_df["captured_at"] = pd.to_datetime(sub_df["captured_at"], errors="coerce")
        sub_df = sub_df.dropna(subset=["captured_at"]).drop_duplicates(subset=["captured_at"]).sort_values("captured_at")
        chart_cols = [c for c in ["qib", "nii", "retail", "total"] if c in sub_df.columns and sub_df[c].notna().any()]
        st.subheader("Subscription history")
        if len(sub_df) >= 2 and chart_cols:
            st.line_chart(sub_df.set_index("captured_at")[chart_cols])
        else:
            st.caption("History will appear after the next few data refreshes.")
    else:
        st.subheader("Subscription history")
        st.caption("History will appear after the next few data refreshes.")

    if gmp_history:
        gmp_df = pd.DataFrame(gmp_history)
        gmp_df["captured_at"] = pd.to_datetime(gmp_df["captured_at"], errors="coerce")
        gmp_df = gmp_df.dropna(subset=["captured_at"]).drop_duplicates(subset=["captured_at"]).sort_values("captured_at")
        st.subheader("GMP history")
        if len(gmp_df) >= 2 and "gmp" in gmp_df.columns and gmp_df["gmp"].notna().any():
            st.line_chart(gmp_df.set_index("captured_at")[["gmp"]])
        else:
            st.caption("History will appear after the next few data refreshes.")
    else:
        st.subheader("GMP history")
        st.caption("History will appear after the next few data refreshes.")

    st.markdown("---")
    st.subheader("Issue details")
    d1, d2 = st.columns(2)
    with d1:
        st.write(f"**Fresh issue:** {money(row.get('fresh_issue'), 2)} Cr")
        st.write(f"**OFS:** {money(row.get('ofs_issue'), 2)} Cr")
        st.write(f"**Listing exchange:** {clean_text(row.get('listing_exchange')) or '—'}")
    with d2:
        st.write(f"**Registrar:** {clean_text(row.get('registrar')) or '—'}")
        st.write(f"**Lead managers:** {clean_text(row.get('lead_managers')) or '—'}")
        st.write(f"**Indicative listing:** {money(row.get('indicative_listing'))}")
    st.caption("GMP is unofficial grey-market information and is not a guarantee of listing price.")
