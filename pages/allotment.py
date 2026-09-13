import streamlit as st
import pandas as pd

from formatters import clean_text, is_missing, money, format_date
from allotment_engine import build_category_plans, optimise, _enrich_allotment_row

def allotment_page(df):
    st.title("Allotment Optimizer")
    st.caption("Use your capital and eligible accounts to maximise the estimated chance of at least one allotment.")

    live = df[df["display_status"] == "Live"].copy()
    mainboard = live[live["segment"].fillna("").str.contains("Mainboard", case=False, na=False)].copy()

    if mainboard.empty:
        st.info("No open Mainboard IPO is available for the optimizer right now.")
        st.caption("SME IPOs use different application rules, so they are intentionally excluded rather than being modelled incorrectly.")
        return

    labels = {
        str(r["source_id"]): clean_text(r.get("company_name")) or "IPO"
        for _, r in mainboard.iterrows()
    }
    selected_id = st.selectbox("IPO", list(labels.keys()), format_func=lambda x: labels[x])
    row = _enrich_allotment_row(mainboard[mainboard["source_id"] == selected_id].iloc[0].to_dict())

    lot_size = None if is_missing(row.get("lot_size")) else int(float(row["lot_size"]))
    price = None if is_missing(row.get("price_high")) else float(row["price_high"])
    if not lot_size or not price:
        st.warning("Price and lot size are required before a strategy can be calculated.")
        return

    lot_value = lot_size * price
    st.markdown(
        f"""<div class=\"calc-hero\">
            <div style=\"font-size:1.05rem;font-weight:750\">{labels[selected_id]}</div>
            <div class=\"small-note\">Mainboard · upper-band lot value {money(lot_value)} · Retail cap ₹2,00,000</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("### 1. Tell us what you have")
    capital = st.number_input(
        "Total capital available (₹)",
        min_value=0.0,
        value=150000.0,
        step=5000.0,
        format="%.0f",
    )
    accounts = st.number_input(
        "Eligible independent PAN / demat accounts",
        min_value=1,
        value=3,
        step=1,
    )

    plans = build_category_plans(row, lot_size, price)
    if not plans:
        st.warning("Category demand data is not available yet. Refresh the IPO data and try again.")
        return

    st.markdown("### 2. Current competition")
    demand_html = '<div class="alloc-grid">'
    for p in plans:
        chance = p.probability * 100
        if chance >= 99.95:
            chance_text = "Likely full allotment"
        elif chance >= 10:
            chance_text = f"~{chance:.1f}% / application"
        else:
            chance_text = f"~1 in {max(1, round(1 / p.probability)):,}"
        source_label = "Application data" if p.source == "application subscription" else "Share-data proxy"
        demand_html += f"""<div class=\"alloc-card\">
            <div class=\"alloc-label\">{p.label.upper()}</div>
            <div class=\"alloc-big\">{chance_text}</div>
            <div class=\"small-note\">Min {money(p.min_amount)} · {p.min_lots} lot(s)</div>
            <div class=\"alloc-source\">{source_label}</div>
        </div>"""
    demand_html += '</div>'
    st.markdown(demand_html, unsafe_allow_html=True)

    st.markdown("### 3. Recommended allocation")
    result = optimise(plans, capital, int(accounts))
    if not result or result["used_accounts"] == 0:
        st.warning("Your capital is not enough for the minimum application available in this IPO.")
        return

    chance = result["chance"]
    st.markdown(
        f"""<div class=\"alloc-result\">
            <div class=\"small-note\">ESTIMATED CHANCE OF AT LEAST ONE ALLOTMENT</div>
            <div class=\"alloc-result-number\">{chance * 100:.1f}%</div>
            <div class=\"small-note\">{result["used_accounts"]} of {int(accounts)} accounts used · {money(result["used_capital"])} of {money(capital)} allocated</div>
        </div>""",
        unsafe_allow_html=True,
    )

    recommendation = []
    for p in plans:
        n = result["counts"].get(p.key, 0)
        if n:
            recommendation.append((p, n))

    for p, n in recommendation:
        st.markdown(
            f"""<div class=\"strategy-row\">
                <div><b>{p.label}</b><div class=\"small-note\">{n} account(s) × {p.min_lots} lot(s)</div></div>
                <div style=\"text-align:right\"><b>{money(n * p.min_amount)}</b><div class=\"small-note\">capital</div></div>
            </div>""",
            unsafe_allow_html=True,
        )

    if result["unused_capital"] > 0:
        st.info(
            f"Keep {money(result['unused_capital'])} unallocated. For the chosen objective, putting more money into an existing account does not create another independent ticket."
        )

    st.markdown("### Why this model is different")
    st.markdown(
        "- **Retail:** focuses on the number of applicants, because oversubscribed retail allotment is lottery-based.\\n"
        "- **sNII / bNII:** treated as separate pools and separate minimum applications, not as a fake `1 ÷ subscription` return.\\n"
        "- **Multiple eligible accounts:** treated as independent applications only when you actually have separate eligible PAN/demat accounts.\\n"
        "- **Minimum application first:** if the goal is at least one allotment, putting extra lots into the same application is not automatically better than creating another eligible application."
    )

    with st.expander("Show the calculation"):
        st.write(
            "For each category, the model estimates the chance of a minimum-size application from application-wise subscription when available. "
            "If a category is subscribed 20× by applications, the starting estimate is about 1/20 per eligible application. "
            "For independent applications, the combined chance is 1 − ∏(1 − pᵢ)ⁿᵢ. The engine checks feasible combinations of categories, capital and accounts and chooses the highest modelled chance."
        )
        st.caption("This is an estimate, not a guarantee. Final allotment depends on valid applications and the registrar's final basis of allotment.")

    last_updated = row.get("subscription_updated_at") or row.get("collected_at")
    st.warning(
        f"Refresh the IPO data before submitting applications. Subscription can change sharply during the final hours. Data last updated: {format_date(last_updated, with_time=True)}."
    )
