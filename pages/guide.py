import streamlit as st

def guide_page():
    st.title("User Guide: IPO Terminal")
    st.markdown("""
    Welcome to the IPO Terminal. This application uses a proprietary quantitative engine and AI to evaluate the fundamental quality and market hype of upcoming public offerings.
    
    ### 🎯 Intended Outputs
    - **CapitalSense QVT Score:** A single, reconciled score (0-100) evaluating the IPO's Quality (financials), Valuation (P/E vs peers), and Trend (subscription velocity & GMP).
    - **AI Analyst Narrative:** A qualitative explanation of *why* the score is what it is, highlighting anchor book data or specific risks from the Red Herring Prospectus.
    - **Trendlyne Consensus:** An external widget showing broader market sentiment for a second opinion.
    
    ### 📥 Required Inputs
    - **IPO Selector:** Choose the specific IPO you want to analyze from the dropdown menu.
    - **Filters:** Use the sidebar to filter by Segment (Mainboard vs SME) or Status (Live, Upcoming, Closed).
    
    ### 💡 Best Practices
    - Trust the **CapitalSense Score** as the primary source of truth. The AI acts only as a narrator, and the Trendlyne widget is purely for external context.
    - SME IPOs inherently carry significantly higher volatility risk and lower liquidity than Mainboard IPOs, regardless of a high Trend score.
    """)
