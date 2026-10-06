import streamlit as st
from agent import analyze, negotiation_email
st.set_page_config(page_title="ClauseGuard", page_icon="🛡️")
st.title("🛡️ ClauseGuard – Rental Agreement Risk Agent")
st.caption("Agentic RAG for tenants. Educational tool, not legal advice.")
up = st.file_uploader("Upload agreement (.txt)", type="txt")
text = up.read().decode("utf-8") if up else st.text_area("…or paste agreement text", height=250)
if st.button("Analyze") and text.strip():
    r = analyze(text)
    st.metric("Risk score", f"{r['risk_score']}/100", r["level"])
    if r["deposit"]: st.info(f"Deposit = {r['deposit']['months']} months' rent" + (" ⚠️" if r["deposit"]["flag"] else " ✅"))
    for f in r["findings"]:
        with st.expander(f"Clause {f['clause_no']}: {', '.join(f['flags'])} (severity {f['severity']})"):
            st.write(f["clause"]); st.markdown("**Why risky:** " + f["explanation"])
            for e in f["evidence"]: st.caption(f"📚 {e['source']} (sim {e['score']}): {e['text'][:200]}")
    st.subheader("Draft negotiation email"); st.code(negotiation_email(r))
