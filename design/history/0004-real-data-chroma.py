"""Chroma's chunking-evaluation gold against ragcourt's loader, and a first retrieval preview (not product code)."""
import csv, json, math, sys, time, urllib.request
from pathlib import Path
from ragcourt import load_documents
from ragcourt.testing import FakeEmbedder

D = Path(sys.argv[1])
docs = {Path(d.id).stem: d.text for d in load_documents(D).documents}
rows = list(csv.DictReader(open(D / "questions_df.csv", encoding="utf-8")))
ok = bad = 0
for r in rows:
    for ref in json.loads(r["references"]):
        text = docs[r["corpus_id"]]
        if text[ref["start_index"]:ref["end_index"]] == ref["content"]: ok += 1
        else: bad += 1
print(f"gold spans exact in loaded text: {ok}/{ok+bad}")

def post(body):
    req = urllib.request.Request("http://localhost:11434/api/embed", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())

def ollama(model, limit):
    def embed(texts):
        return [post({"model": model, "input": [t], "options": {"num_ctx": limit, "num_batch": limit}})["embeddings"][0] for t in texts]
    return embed

def fake(texts): return FakeEmbedder().embed(texts).vectors

def chunks_of(text, size=800, overlap=0):
    out, start = [], 0
    while start < len(text):
        out.append((start, min(len(text), start + size))); start += size - overlap
    return out

def cos(a, b):
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0

for corpus in sys.argv[2:]:
    text = docs[corpus]; spans = chunks_of(text)
    qs = [r for r in rows if r["corpus_id"] == corpus]
    for name, embed in (("fake", fake), ("nomic-embed-text", ollama("nomic-embed-text", 2048)), ("mxbai-embed-large", ollama("mxbai-embed-large", 512))):
        t0 = time.time()
        vecs = embed([text[s:e] for s, e in spans]); qv = embed([q["question"] for q in qs])
        hits = cut = 0
        for q, v in zip(qs, qv):
            refs = json.loads(q["references"])
            whole = [i for i, (s, e) in enumerate(spans) if all(s <= r["start_index"] and r["end_index"] <= e for r in refs[:1])]
            if not whole: cut += 1; continue
            top = sorted(range(len(spans)), key=lambda i: -cos(v, vecs[i]))[:5]
            hits += whole[0] in top
        print(f"{corpus:22s} {name:18s} hit@5={hits}/{len(qs)}  first quote cut by 800-char chunks: {cut}  ({time.time()-t0:.0f}s)")
