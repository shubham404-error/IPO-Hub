import streamlit as st

from ai_advisor import get_gemini_api_key, chat_with_advisor, build_ai_dataset

def ai_analyst_page(df):
    st.title("AI Analyst")
    st.caption("Ask deeper questions about the IPOs currently tracked by IPO Intelligence.")

    if not get_gemini_api_key():
        st.warning("AI is not configured. Add GEMINI_API_KEY to Streamlit secrets to use the analyst.")
        return

    st.markdown("#### Start with a question")
    prompts = [
        "Which open IPO looks best for listing gains?",
        "Which IPO has the best risk/reward right now?",
        "Which IPOs should I avoid and why?",
        "Compare the top 3 open IPOs for me.",
    ]
    cols = st.columns(2)
    for i, prompt in enumerate(prompts):
        with cols[i % 2]:
            if st.button(prompt, key=f"analyst_prompt_{i}", use_container_width=True):
                st.session_state["ai_pending_prompt"] = prompt

    pending = st.session_state.pop("ai_pending_prompt", None)
    if pending:
        st.session_state["ai_chat_messages"].append({"role": "user", "content": pending})
        try:
            answer = chat_with_advisor(
                pending,
                analysis={"recommendations": list(st.session_state["ai_scores"].values())},
                ipos=build_ai_dataset(df),
            )
            st.session_state["ai_chat_messages"].append({"role": "assistant", "content": answer})
        except Exception as exc:
            st.error(f"AI error: {exc}")

    for message in st.session_state["ai_chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask about an IPO, listing gains, allotment, risks...")
    if question:
        st.session_state["ai_chat_messages"].append({"role": "user", "content": question})
        try:
            answer = chat_with_advisor(
                question,
                analysis={"recommendations": list(st.session_state["ai_scores"].values())},
                ipos=build_ai_dataset(df),
            )
            st.session_state["ai_chat_messages"].append({"role": "assistant", "content": answer})
            st.rerun()
        except Exception as exc:
            st.error(f"AI error: {exc}")
