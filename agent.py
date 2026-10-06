"""ClauseGuard agent: split -> detect (rule tools) -> retrieve (RAG) -> explain (LLM/fallback) -> score -> negotiate."""
import os, re, sys
from rag import Retriever

KB = os.path.join(os.path.dirname(__file__), "data", "kb")
MODEL = os.environ.get("CLAUSEGUARD_MODEL", "claude-sonnet-5-5")

# (id, regex, severity 1-3, title, retrieval query)
RULES = [
    ("AUTO_RENEW", r"automatic(ally)? renew|auto[- ]renew", 2, "Automatic renewal", "automatic renewal agreement term"),
    ("DEPOSIT_FORFEIT", r"(deposit|advance).{0,60}(forfeit|non[- ]refundable|shall not be refund)", 3, "Deposit forfeiture / non-refundable", "security deposit refund deductions"),
    ("LOCK_IN", r"lock[- ]in|minimum (stay|period) of (\d+) months", 2, "Lock-in period", "lock-in period early exit penalty"),
    ("ENTRY", r"(enter|access|inspect).{0,60}(any time|without (prior )?(notice|consent))", 3, "Landlord entry without notice", "landlord entry notice privacy"),
    ("HIKE", r"(increase|revise|escalat).{0,50}(\d+)\s*%", 2, "Rent escalation clause", "rent increase notice revision"),
    ("EVICT", r"(vacate|evict|terminate).{0,60}(immediately|without (any )?notice|at (his|its|their) sole discretion)", 3, "Unilateral termination / eviction", "eviction termination notice period"),
    ("REPAIR", r"(all|any) (repairs?|maintenance).{0,50}(tenant|lessee|licensee)", 2, "All repairs on tenant", "repairs maintenance responsibility structural"),
    ("PENALTY", r"penalt(y|ies)|liquidated damages|fine of", 2, "Penalty clause", "penalty damages reasonable compensation"),
    ("UNREG", r"not (be )?registered|no need (to|for) regist|unregistered", 2, "Agreement not registered", "registration stamp duty agreement"),
]

def split_clauses(text):
    parts = re.split(r"\n\s*(?=\d+[\.\)]\s)", text.strip())
    return [re.sub(r"\s+", " ", p).strip() for p in parts if len(p.strip()) > 20]

def tool_deposit_check(text):
    """Document-level numeric tool: deposit vs monthly rent."""
    num = lambda s: int(s.replace(",", ""))
    r = re.search(r"monthly rent[^.\d]{0,30}(?:rs\.?|inr|₹)\s*([\d,]+)", text, re.I)
    d = re.search(r"(?:security )?deposit[^.\d]{0,30}(?:rs\.?|inr|₹)\s*([\d,]+)", text, re.I)
    if r and d:
        rent, dep = num(r.group(1)), num(d.group(1))
        months = round(dep / rent, 1)
        return {"rent": rent, "deposit": dep, "months": months, "flag": months > 2}
    return None

def llm_explain(clause, flags, evidence):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import anthropic
            ev = "\n".join(f"- {t}" for (_, t), _ in evidence) or "- (none)"
            msg = anthropic.Anthropic(api_key=key).messages.create(
                model=MODEL, max_tokens=300,
                messages=[{"role": "user", "content":
                    f"You help tenants understand rental agreements. Using ONLY the guidance below, explain in 2-3 plain sentences why this clause is risky and suggest a fairer wording. Not legal advice.\n\nClause: {clause}\nFlags: {', '.join(flags)}\nGuidance:\n{ev}"}])
            return msg.content[0].text
        except Exception as e:
            pass
    ev = evidence[0][0][1] if evidence else "No matching guidance found."
    return f"Flagged: {', '.join(flags)}. Reference guidance: {ev}"

def analyze(text, retriever=None):
    rt = retriever or Retriever(KB)
    results, score = [], 0
    for i, c in enumerate(split_clauses(text), 1):
        hits = [(rid, sev, title, q) for rid, rx, sev, title, q in RULES if re.search(rx, c, re.I)]
        if not hits: continue
        evidence = rt.search(" ".join(h[3] for h in hits), k=2)
        sev = max(h[1] for h in hits); score += sum(h[1] for h in hits)
        results.append({"clause_no": i, "clause": c, "flags": [h[2] for h in hits], "severity": sev,
                        "evidence": [{"source": s, "text": t, "score": sc} for (s, t), sc in evidence],
                        "explanation": llm_explain(c, [h[2] for h in hits], evidence)})
    dep = tool_deposit_check(text)
    if dep and dep["flag"]: score += 3
    risk = min(100, score * 8)
    level = "HIGH" if risk >= 60 else "MEDIUM" if risk >= 30 else "LOW"
    return {"risk_score": risk, "level": level, "deposit": dep, "findings": results}

def negotiation_email(report):
    pts = [f"- Clause {f['clause_no']} ({', '.join(f['flags'])}): please revise to a balanced, notice-based wording."
           for f in report["findings"]]
    if report["deposit"] and report["deposit"]["flag"]:
        pts.append(f"- Security deposit is {report['deposit']['months']} months' rent; I request it be reduced to 2 months.")
    return "Subject: Request for revisions to the rental agreement\n\nDear Sir/Madam,\n\nBefore signing, I request the following changes:\n" + "\n".join(pts) + "\n\nKindly confirm so we can proceed.\n\nRegards"

if __name__ == "__main__":
    r = analyze(open(sys.argv[1], encoding="utf-8").read())
    print(f"RISK {r['risk_score']}/100 [{r['level']}]  deposit={r['deposit']}")
    for f in r["findings"]:
        print(f"\n#{f['clause_no']} {f['flags']}\n  {f['explanation'][:220]}")
    print("\n" + negotiation_email(r))
