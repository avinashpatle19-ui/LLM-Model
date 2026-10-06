"""Tiny dependency-free TF-IDF retriever over the tenancy knowledge base."""
import glob, math, os, re
from collections import Counter
TOK = re.compile(r"[a-z0-9]+")
STOP = set("the a an of to and or in on is are be by for with as at it this that shall will".split())
def tok(t): return [w for w in TOK.findall(t.lower()) if w not in STOP]

class Retriever:
    def __init__(self, kb_dir):
        self.docs = []
        for f in sorted(glob.glob(os.path.join(kb_dir, "*.txt"))):
            for p in open(f, encoding="utf-8").read().split("\n\n"):
                if p.strip(): self.docs.append((os.path.basename(f), p.strip()))
        tfs = [Counter(tok(d[1])) for d in self.docs]
        df = Counter(w for c in tfs for w in c)
        n = len(self.docs)
        self.idf = {w: math.log((1 + n) / (1 + v)) + 1 for w, v in df.items()}
        self.vecs = [self._vec(c) for c in tfs]
    def _vec(self, c):
        v = {w: f * self.idf.get(w, 0) for w, f in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        return {w: x / norm for w, x in v.items()}
    def search(self, query, k=2):
        q = self._vec(Counter(tok(query)))
        scored = sorted(((sum(x * d.get(w, 0) for w, x in q.items()), i)
                         for i, d in enumerate(self.vecs)), reverse=True)
        return [(self.docs[i], round(s, 2)) for s, i in scored[:k] if s > 0.05]
