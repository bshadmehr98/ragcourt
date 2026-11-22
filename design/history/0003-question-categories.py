"""Feasibility: can a local model write questions of each category, and can code verify the category?

Not product code. argv: corpus dir, output json, model.
"""

import json
import math
import random
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

OLLAMA = "http://localhost:11434"
WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*")
STOP = set("""a an the of to in on for and or is are was were be been it this that with as by at from what which
who how when where why does do did can could should would will not no any all into than then there their
its your you we they he she i me my our out up about over under via per""".split())
NEG = re.compile(r"\b(not|never|no|without|except|unless|cannot|can't|doesn't|isn't|won't)\b", re.I)


def post(path, body):
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def chat(model, prompt):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False,
            "options": {"temperature": 0, "seed": 1}, "think": False, "format": "json"}
    r = post("/api/chat", body)
    text = re.sub(r"<think>.*?</think>", "", r["message"]["content"], flags=re.S).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def words(t):
    return [w.lower() for w in WORD.findall(t)]


def content(t):
    return {w for w in words(t) if w not in STOP and len(w) > 2}


def found(hay, needle):
    if not needle:
        return False
    if needle in hay:
        return True
    pat = r"\s+".join(re.escape(w) for w in needle.split())
    return bool(re.search(pat, hay))


ASK = {
    "paraphrase": "a question that uses DIFFERENT words from the passage (no distinctive word of the quote may "
                  "appear in the question; use synonyms and rephrasing)",
    "keyword": "a keyword search, 2 to 5 words, no question mark, the way a user types into a search box",
    "exact_term": "a question that must contain this exact term from the passage: {term}",
    "negation": "a question about what something does NOT do, cannot do, or the exception to a rule, "
                "answered by the passage",
    "numeric": "a question whose answer is a number, a default value, a limit, a version or a date stated in "
               "the passage",
    "distractor": "a question answered by the PASSAGE, but worded with the vocabulary of the OTHER passage below "
                  "(which does NOT answer it), so that a search engine could be misled to the other passage.\n"
                  "OTHER passage:\n\"\"\"{other}\"\"\"",
}

PROMPT = """You write one test question for a search system. Write {ask}.
Copy an exact quote (one to three consecutive sentences, character for character) from the PASSAGE that answers it.
Reply JSON only: {{"question": "...", "quote": "..."}}

PASSAGE:
\"\"\"{passage}\"\"\""""


def check(cat, q, quote, passage, term, other, df, ndocs):
    """Code check of the category. Returns (ok, why)."""
    qw, uw = content(q), content(quote)
    if cat == "paraphrase":
        j = len(qw & uw) / max(len(qw | uw), 1)
        return j < 0.15, f"jaccard={j:.2f}"
    if cat == "keyword":
        n = len(q.split())
        return 2 <= n <= 6 and "?" not in q, f"words={n}"
    if cat == "exact_term":
        return term.lower() in q.lower() and term.lower() in quote.lower(), f"term={term}"
    if cat == "negation":
        return bool(NEG.search(q)) and bool(NEG.search(quote)), "negation in question and quote"
    if cat == "numeric":
        return bool(re.search(r"\d", quote)), "digit in quote"
    if cat == "distractor":
        ov_gold = len(qw & content(passage)) / max(len(qw), 1)
        ov_other = len(qw & content(other)) / max(len(qw), 1)
        return ov_other > ov_gold, f"overlap other={ov_other:.2f} gold={ov_gold:.2f}"
    return False, "?"


def main():
    root, out, model = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    docs = {p.name: p.read_text() for p in sorted(root.glob("*.md"))}
    paras = [(n, p) for n, t in docs.items() for p in re.split(r"\n\s*\n", t) if len(p) > 300]
    df = Counter(w for t in docs.values() for w in set(words(t)))
    rnd = random.Random(11)
    sample = rnd.sample(paras, 8)
    res = {"model": model, "by_category": {}, "samples": []}
    for cat in ASK:
        stats = {"asked": 0, "verbatim": 0, "category_ok": 0, "s": 0.0}
        for name, passage in sample:
            rare = sorted({w for w in WORD.findall(passage) if df[w.lower()] <= 2 and len(w) > 3 and not w.isdigit()},
                          key=lambda w: (df[w.lower()], w))
            term = rare[0] if rare else ""
            if cat == "exact_term" and not term:
                continue
            pw = content(passage)
            other = max((p for n2, p in paras if p != passage),
                        key=lambda p: len(pw & content(p)) / math.sqrt(len(content(p)) + 1))
            ask = ASK[cat].format(term=term, other=other[:1500])
            t0 = time.time()
            r = chat(model, PROMPT.format(ask=ask, passage=passage[:2500]))
            stats["s"] += time.time() - t0
            stats["asked"] += 1
            q, quote = str(r.get("question", "")), str(r.get("quote", ""))
            v = found(passage, quote)
            ok, why = check(cat, q, quote, passage, term, other, df, len(docs))
            stats["verbatim"] += v
            stats["category_ok"] += v and ok
            res["samples"].append({"cat": cat, "q": q, "quote": quote[:160], "verbatim": v, "ok": ok, "why": why})
        stats["s_per_q"] = round(stats.pop("s") / max(stats["asked"], 1), 2)
        res["by_category"][cat] = stats
        print(cat, stats, flush=True)
    out.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
