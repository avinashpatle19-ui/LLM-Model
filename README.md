# ClauseGuard 🛡️
Agentic RAG tool that analyzes rental agreements and flags risky clauses.
## Run
```
pip install -r requirements.txt
python agent.py samples/risky_agreement.txt     # CLI
streamlit run app.py                            # Web UI
export ANTHROPIC_API_KEY=...                    # optional: LLM explanations (otherwise offline fallback)
```
## Files
agent.py (workflow + tools) · rag.py (retriever) · app.py (UI) · data/kb (knowledge base) · docs/REPORT_OUTLINE.md
Disclaimer: educational project; the sample KB must be verified against official law.
