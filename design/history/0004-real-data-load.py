"""Load real corpora with ragcourt.load_documents and check what came out (not product code)."""
import re, sys, time
from collections import Counter
from pathlib import Path
from ragcourt import load_documents

for folder in sys.argv[1:]:
    root = Path(folder)
    t = time.time()
    corpus = load_documents(root)
    ms = (time.time() - t) * 1000
    chars = sum(len(d.text) for d in corpus.documents)
    print(f"\n== {root.name}: {len(corpus.documents)} docs, {chars/1e6:.2f}M chars, {ms:.0f} ms, skipped {len(corpus.skipped)}")
    for s in corpus.skipped[:5]:
        print("   skipped:", s.path, "-", s.reason)
    problems = Counter()
    for d in corpus.documents:
        p = root / d.id
        if p.suffix.lower() in (".html", ".htm"):
            fences = d.text.count("\n```\n") + d.text.startswith("```\n")
            if "\x00" in d.text: problems["NUL marker leaked"] += 1
            if len(re.findall(r"^```", d.text, re.M)) % 2: problems["odd number of fences"] += 1
            if re.search(r"<[a-z]+[^>]*>", d.text): problems["tag-like text left (may be literal)"] += 1
            if len(d.text.strip()) < 200: problems["almost empty"] += 1
        else:
            raw = p.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
            if raw != d.text: problems["text changed"] += 1
        if not d.text.endswith("\n") and d.text: problems["no final newline (info)"] += 1
    print("   problems:", dict(problems) or "none")
