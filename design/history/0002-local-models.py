"""Feasibility experiment: can local Ollama models give a first useful ragdoctor result in under a minute?

Not product code. Measures, on a Markdown corpus given as argv[1]:
  E1 embedding models: load time, throughput, dimension.
  E2 chat models: question+quote generation time and verbatim rate.
  E3 closed-book answer + judge time per question.
Writes JSON to argv[2].
"""

import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA = "http://localhost:11434"
ERRORS = []
JUDGE = None
JUDGE_PROMPT = """You are a strict grader. The reference quote is the only truth.
Question: {question}
Reference quote: {quote}
Candidate answer: {answer}
The candidate is correct only if it states the specific fact the reference quote gives. A refusal, UNKNOWN,
a request for more context, a guess, or a generic answer that would fit many systems is NOT correct.
Reply JSON: {{"correct": true or false, "reason": "a few words"}}"""


def post(path, body, timeout=600):
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def unload(model):
    try:
        post("/api/generate", {"model": model, "keep_alive": 0}, timeout=60)
    except Exception:
        pass


def chunks_of(docs, size=1200):
    out = []
    for text in docs.values():
        paras = [p for p in text.split("\n\n") if p.strip()]
        cur = ""
        for p in paras:
            if len(cur) + len(p) > size and cur:
                out.append(cur)
                cur = ""
            cur += p + "\n\n"
        if cur.strip():
            out.append(cur)
    return out


def e1_embed(model, chunks):
    unload(model)
    t0 = time.time()
    first = post("/api/embed", {"model": model, "input": ["warm up"]})
    load_s = time.time() - t0
    t0 = time.time()
    dims = None
    for i in range(0, len(chunks), 32):
        r = post("/api/embed", {"model": model, "input": chunks[i : i + 32], "truncate": True})
        dims = len(r["embeddings"][0])
    dt = time.time() - t0
    unload(model)
    errs = [e for e in ERRORS if e.startswith(model)]
    return {"model": model, "errors": len(errs), "first_error": errs[:1], "load_s": round(load_s, 2), "chunks": len(chunks), "embed_s": round(dt, 2),
            "chunks_per_s": round(len(chunks) / dt, 1), "dim": dims or len(first["embeddings"][0])}


PROMPT = """You write test questions for a search system. Read the passage and write {n} questions that the
passage answers. For each, copy an exact quote (one to three consecutive sentences, copied character for
character) from the passage that answers it. Make the first question a paraphrase (different words from
the passage) and the second keyword-style (a few search terms, like a user types into a search box).
Reply with JSON only: {{"questions": [{{"question": "...", "quote": "...", "style": "paraphrase|keyword"}}]}}

Passage:
\"\"\"
{passage}
\"\"\""""


def norm_find(hay, needle):
    if needle in hay:
        return "exact"
    pat = r"\s+".join(re.escape(w) for w in needle.split())
    return "whitespace" if pat and re.search(pat, hay) else None


def chat(model, prompt, fmt=None, think=False):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False,
            "options": {"temperature": 0, "seed": 1}, "think": think}
    if fmt:
        body["format"] = fmt
    t0 = time.time()
    try:
        r = post("/api/chat", body)
    except Exception as e:  # recorded, not fatal: count failures per model
        ERRORS.append(f"{model}: {e}")
        return "", time.time() - t0, 0
    text = re.sub(r"<think>.*?</think>", "", r["message"]["content"], flags=re.S).strip()
    if fmt and not text.startswith("{"):
        m = re.search(r"\{.*\}", text, re.S)
        text = m.group(0) if m else text
    return text, time.time() - t0, r.get("eval_count", 0)


def e2_e3(model, windows, docs_joined):
    unload(model)
    t0 = time.time()
    chat(model, "Say OK.")
    load_s = time.time() - t0
    gen = []
    t_gen = 0.0
    toks = 0
    for w in windows:
        text, dt, n = chat(model, PROMPT.format(n=2, passage=w), fmt="json")
        t_gen += dt
        toks += n
        try:
            qs = json.loads(text).get("questions", [])
        except (json.JSONDecodeError, AttributeError):
            qs = []
        for q in qs:
            if not isinstance(q, dict):
                continue
            found = norm_find(w, str(q.get("quote", "")))
            gen.append({**q, "found": found})
    kept = [q for q in gen if q["found"]]
    # E3 on kept questions: closed-book answer, then a judge call.
    t_cb = t_judge = 0.0
    judged = []
    for q in kept[:10]:
        ans, dt, _ = chat(model, "Answer briefly from your own knowledge, in one or two sentences. If you do not know the "
                          f"specific answer, reply exactly UNKNOWN. Question: {q['question']}")
        t_cb += dt
        verdict, dt, _ = chat(JUDGE or model, JUDGE_PROMPT.format(quote=q["quote"], question=q["question"],
                              answer=ans), fmt="json")
        t_judge += dt
        judged.append({"question": q["question"], "closed_book": ans[:200], "verdict": verdict})
    unload(model)
    n_kept = max(len(kept[:10]), 1)
    errs = [e for e in ERRORS if e.startswith(model)]
    return {"model": model, "errors": len(errs), "first_error": errs[:1], "load_s": round(load_s, 2), "windows": len(windows), "generated": len(gen),
            "verbatim_exact": sum(q["found"] == "exact" for q in gen),
            "verbatim_ws": sum(q["found"] == "whitespace" for q in gen),
            "gen_s_per_window": round(t_gen / len(windows), 2), "gen_tokens": toks,
            "closed_book_s_per_q": round(t_cb / n_kept, 2), "judge_s_per_q": round(t_judge / n_kept, 2),
            "judged": judged, "samples": gen[:6]}


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    docs = {p.name: p.read_text() for p in sorted(root.glob("*.md"))}
    chunks = chunks_of(docs)
    rnd = random.Random(7)
    windows = [c for c in rnd.sample(chunks, 10)]
    global JUDGE
    JUDGE = sys.argv[5] if len(sys.argv) > 5 else None
    embedders = [m for m in sys.argv[3].split(",") if m]
    chats = [m for m in sys.argv[4].split(",") if m]
    res = {"corpus_docs": len(docs), "corpus_chars": sum(map(len, docs.values())), "embed": [], "chat": []}
    for m in embedders:
        try:
            res["embed"].append(e1_embed(m, chunks))
        except Exception as e:
            res["embed"].append({"model": m, "error": str(e)})
        print(res["embed"][-1], flush=True)
        out.write_text(json.dumps(res, indent=2))
    for m in chats:
        r = e2_e3(m, windows, "")
        res["chat"].append(r)
        print({k: v for k, v in r.items() if k not in ("judged", "samples")}, flush=True)
        out.write_text(json.dumps(res, indent=2))
    out.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
