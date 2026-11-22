"""HTML becomes Markdown-shaped text (design §4.1)."""

from ragcourt.io.html_text import html_to_text


def test_headings_become_hash_lines() -> None:
    text = html_to_text("<h1>Title</h1><p>Intro.</p><h3>Deep</h3><p>More.</p>")
    assert text == "# Title\n\nIntro.\n\n### Deep\n\nMore.\n"


def test_table_rows_become_pipe_lines() -> None:
    html = "<table>\n<tr><th>A</th><th>B</th></tr>\n<tr><td> 1 </td><td>two\nwords</td></tr>\n</table>"
    assert html_to_text(html) == "| A | B |\n| 1 | two words |\n"


def test_pre_becomes_a_fenced_block_with_its_indentation() -> None:
    html = "<p>Run:</p><pre>\nif x:\n    go()\n</pre><p>Done.</p>"
    assert html_to_text(html) == "Run:\n\n```\nif x:\n    go()\n```\n\nDone.\n"


def test_scripts_styles_and_head_are_dropped() -> None:
    html = "<head><title>T</title><style>p {}</style></head><p>Kept.</p><script>var x;</script>"
    assert html_to_text(html) == "Kept.\n"


def test_whitespace_collapses_and_entities_are_decoded() -> None:
    assert html_to_text("<p>a   b\n\n c &amp; d</p>") == "a b c & d\n"


def test_list_items_and_breaks_start_lines() -> None:
    assert html_to_text("<ul><li>one</li><li>two</li></ul>x<br>y") == "one\ntwo\n\nx\ny\n"


def test_stray_end_tags_are_ignored() -> None:
    assert html_to_text("</pre></tr></script><p>ok</p>") == "ok\n"
