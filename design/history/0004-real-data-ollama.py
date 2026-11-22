"""Probe what Ollama's embedding API really reports (not product code)."""
import json, sys, urllib.request, math

URL = "http://localhost:11434"

def post(path, body):
    req = urllib.request.Request(URL + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:300]}

def cos(a, b):
    return sum(x*y for x, y in zip(a, b)) / math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))

word = "retry "
for model in sys.argv[1:]:
    show = post("/api/show", {"model": model})
    ctx = {k: v for k, v in show.get("model_info", {}).items() if k.endswith("context_length")}
    params = show.get("parameters", "")
    one = post("/api/embed", {"model": model, "input": ["hello world"]})
    two = post("/api/embed", {"model": model, "input": ["hello world", "hello world, hello world again"]})
    single_b = post("/api/embed", {"model": model, "input": ["hello world, hello world again"]})
    limit = list(ctx.values())[0] if ctx else 2048
    long_text = word * int(limit * 1.5)
    trunc = post("/api/embed", {"model": model, "input": [long_text]})
    notrunc = post("/api/embed", {"model": model, "input": [long_text], "truncate": False})
    mid = word * 3000
    mid_r = post("/api/embed", {"model": model, "input": [mid]})
    mid_big = post("/api/embed", {"model": model, "input": [mid], "options": {"num_ctx": limit}})
    print(json.dumps({
        "model": model, "context_length": ctx, "parameters": params.replace("\n", "; "),
        "count_one": one.get("prompt_eval_count"), "count_batch_of_two": two.get("prompt_eval_count"),
        "count_second_alone": single_b.get("prompt_eval_count"),
        "batch_equals_single": round(cos(two["embeddings"][1], single_b["embeddings"][0]), 6) if "embeddings" in two else None,
        "over_limit_default": trunc.get("prompt_eval_count", trunc),
        "over_limit_truncate_false": notrunc.get("prompt_eval_count", notrunc),
        "3000_words_default": mid_r.get("prompt_eval_count", mid_r),
        "3000_words_num_ctx_limit": mid_big.get("prompt_eval_count", mid_big),
    }))
    sys.stdout.flush()
