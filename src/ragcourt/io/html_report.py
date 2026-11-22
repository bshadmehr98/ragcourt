"""The HTML report: one self-contained file from ``results.json`` (design §13.4, D-019).

Standard-library templating (``html.escape``), inline CSS, a few lines of inline JavaScript to filter the
misses by category; no network request when opened.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

REPORT = "report.html"
STYLE = """
body{font:15px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:72rem;padding:0 1rem;
color:#1d2433;background:#fff}
h1,h2{line-height:1.2}table{border-collapse:collapse;margin:.5rem 0 1rem;width:100%}
td,th{border-bottom:1px solid #dde2ea;padding:.3rem .5rem;text-align:left;vertical-align:top}
.bar{position:relative;height:.6rem;background:#eef1f6;border-radius:3px;min-width:8rem}
.bar span{position:absolute;top:0;height:.6rem;background:#7aa2e3;border-radius:3px}
.bar i{position:absolute;top:-.2rem;width:2px;height:1rem;background:#1d2433}
.tie{color:#a15c00;font-weight:600}.note{color:#5b6475}details{margin:.4rem 0}
pre{white-space:pre-wrap;background:#f6f8fb;padding:.6rem;border-radius:4px}
@media (prefers-color-scheme:dark){body{background:#12161f;color:#e4e8ef}td,th{border-color:#2b3242}
pre,.bar{background:#1c2230}.bar i{background:#e4e8ef}.note{color:#9aa3b5}}
"""
SCRIPT = """
function only(category){document.querySelectorAll('[data-category]').forEach(function(item){
item.style.display=(category===''||item.dataset.category===category)?'':'none';});}
"""


def write_report(folder: Path, results: dict[str, Any], mechanisms: dict[str, str]) -> Path:
    """Write ``report.html`` beside ``results.json`` and return its path."""
    path = folder / REPORT
    path.write_text(report_html(results, mechanisms), encoding="utf-8")
    return path


def report_html(results: dict[str, Any], mechanisms: dict[str, str]) -> str:
    """The whole report."""
    parts = [
        f"<h1>ragcourt run {_e(results['run'])}</h1>",
        f"<p>Chosen pipeline: <b>{_e(results['chosen'])}</b></p>",
    ]
    parts += [_board(board) for board in results["boards"]]
    parts.append(_ceilings(results["ceilings"]))
    parts.append(_misses(results["blames"], mechanisms))
    if results.get("audit"):
        parts.append(_audit(results["audit"]))
    head = (
        f"<meta charset='utf-8'><title>ragcourt report</title><style>{STYLE}</style><script>{SCRIPT}</script>"
    )
    return f"<!doctype html><html lang='en'><head>{head}</head><body>{''.join(parts)}</body></html>\n"


def _e(value: object) -> str:
    return html.escape(str(value))


def _interval(value: dict[str, float]) -> str:
    return f"{value['mean']:.2f} [{value['low']:.2f}, {value['high']:.2f}]"


def _bar(value: dict[str, float]) -> str:
    low, high, mean = (max(0.0, min(1.0, value[key])) * 100 for key in ("low", "high", "mean"))
    span = f"<span style='left:{low:.1f}%;width:{max(high - low, 0.5):.1f}%'></span>"
    mark = f"<i style='left:{mean:.1f}%'></i>"
    return f"<div class='bar' title='{_e(_interval(value))}'>{span}{mark}</div>"


def _board(board: dict[str, Any]) -> str:
    rows: list[str] = []
    for row in board["rows"]:
        tie = "<span class='tie'>= </span>" if row["tied_with_top"] else ""
        cells = f"<td>{tie}{_e(row['label'])}</td><td>{_interval(row['overall'])}</td>"
        rows.append(f"<tr>{cells}<td>{_bar(row['overall'])}</td></tr>")
    if board.get("indicative"):
        verdict = "Every category has too few held-out questions to rank: indicative only, no winner."
    elif board["winner"]:
        verdict = f"Winner: {_e(board['winner'])}"
    else:
        verdict = "No significant difference at the top: no winner."
    title = f"<h2>{_e(board['stage'])}s <small class='note'>({_e(board['metric'])}, held-out)</small></h2>"
    head = "<tr><th>pipeline</th><th>overall [95%]</th><th>interval</th></tr>"
    return f"{title}<table>{head}{''.join(rows)}</table><p>{verdict}</p>"


def _ceilings(ceilings: dict[str, Any]) -> str:
    rows: list[str] = []
    for name, value in ceilings.items():
        levels = "".join(f"<td>{value[level]:.2f}</td>" for level in ("chunker", "retrieval", "hit_at_k"))
        rows.append(f"<tr><td>{_e(name)}</td><td>{value['questions']}</td>{levels}</tr>")
    head = "<tr><th>group</th><th>questions</th><th>chunker</th><th>retrieval</th><th>hit@k</th></tr>"
    return f"<h2>Ceilings</h2><table>{head}{''.join(rows)}</table>"


def _misses(blames: list[dict[str, Any]], mechanisms: dict[str, str]) -> str:
    categories = sorted({str(blame["category"]) for blame in blames})
    buttons = "".join(f"<button onclick=\"only('{_e(name)}')\">{_e(name)}</button> " for name in categories)
    items = [_miss(blame, mechanisms) for blame in sorted(blames, key=lambda item: str(item["mechanism"]))]
    filters = f"<p><button onclick=\"only('')\">all</button> {buttons}</p>"
    body = "".join(items) or "<p>No held-out question was missed.</p>"
    return f"<h2>Misses ({len(blames)})</h2>{filters}{body}"


def _miss(blame: dict[str, Any], mechanisms: dict[str, str]) -> str:
    summary = f"<b>{_e(blame['mechanism'])}</b> ({_e(blame['level'])}): {_e(blame['text'])}"
    meaning = _e(mechanisms.get(str(blame["mechanism"]), ""))
    body = f"<p class='note'>{meaning}</p><p>Evidence: {_e(blame['evidence'])}</p>"
    body += f"<p>Fix: {_e(blame['fix'])}</p><pre>{_e(blame['context'])}</pre>"
    return f"<details data-category='{_e(blame['category'])}'><summary>{summary}</summary>{body}</details>"


def _audit(audit: dict[str, Any]) -> str:
    rows = "".join(f"<tr><td>{_e(code)}</td><td>{count}</td></tr>" for code, count in audit["counts"].items())
    return f"<h2>Audit of the chosen chunker ({_e(audit['chunker'])})</h2><table>{rows}</table>"
