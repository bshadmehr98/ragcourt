"""Do embedders' documented query/document prefixes change the ranking? (not product code)"""
import csv, json, math, sys, urllib.request
from pathlib import Path
from ragcourt import load_documents
D = Path(sys.argv[1])
docs = {Path(d.id).stem: d.text for d in load_documents(D).documents}
rows = list(csv.DictReader(open(D / "questions_df.csv", encoding="utf-8")))
def post(body):
    req = urllib.request.Request("http://localhost:11434/api/embed", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())
def embed(model, limit, texts):
    return [post({"model": model, "input": [t], "options": {"num_ctx": limit, "num_batch": limit}})["embeddings"][0] for t in texts]
def cos(a, b): return sum(x*y for x, y in zip(a, b)) / math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))
SETUPS = [
    ("nomic-embed-text", 2048, "", ""),
    ("nomic-embed-text", 2048, "search_query: ", "search_document: "),
    ("mxbai-embed-large", 512, "", ""),
    ("mxbai-embed-large", 512, "Represent this sentence for searching relevant passages: ", ""),
    ("embeddinggemma", 2048, "", ""),
    ("embeddinggemma", 2048, "task: search result | query: ", "title: none | text: "),
]
for corpus in sys.argv[2:]:
    text = docs[corpus]; spans = [(s, min(len(text), s + 800)) for s in range(0, len(text), 800)]
    qs = [r for r in rows if r["corpus_id"] == corpus]
    for model, limit, qp, dp in SETUPS:
        vecs = embed(model, limit, [dp + text[s:e] for s, e in spans]); qv = embed(model, limit, [qp + q["question"] for q in qs])
        hits = n = 0
        for q, v in zip(qs, qv):
            r0 = json.loads(q["references"])[0]
            whole = [i for i, (s, e) in enumerate(spans) if s <= r0["start_index"] and r0["end_index"] <= e]
            if not whole: continue
            n += 1
            hits += whole[0] in sorted(range(len(spans)), key=lambda i: -cos(v, vecs[i]))[:5]
        print(f"{corpus:20s} {model:18s} prefixes={'yes' if qp else 'no ':3s} hit@5={hits}/{n}")
