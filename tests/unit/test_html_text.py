"""HTML becomes Markdown-shaped text (design §4.1), including HTML that leaves end tags out."""

import pytest

from ragcourt.io.html_text import html_to_text


@pytest.mark.parametrize(
    ("html", "text"),
    [
        # Headings, paragraphs, lists and line breaks.
        ("<h1>Title</h1><p>Intro.</p><h3>Deep</h3><p>More.</p>", "# Title\n\nIntro.\n\n### Deep\n\nMore.\n"),
        ("<h2>\n  Install\n</h2>", "## Install\n"),
        ("<ul><li>one</li><li>two</li></ul>x<br>y", "one\ntwo\n\nx\ny\n"),
        ("<p>a   b\n\n c &amp; d</p>", "a b c & d\n"),
        ("<p>foo <b> bar</b>baz</p>", "foo barbaz\n"),
        # tables: a separator under the first row, implied end tags, nested content
        (
            "<table>\n<tr><th>A</th><th>B</th></tr>\n<tr><td> 1 </td><td>two\nwords</td></tr>\n</table>",
            "| A | B |\n| --- | --- |\n| 1 | two words |\n",
        ),
        ("<table><tr><td>a<td>b<tr><td>c<td>d</table>", "| a | b |\n| --- | --- |\n| c | d |\n"),
        ("<table><tr><td>a</td><td>b</td></table><p>after</p>", "| a | b |\n| --- | --- |\n\nafter\n"),
        ("<table><tr><td>a<b>b</b></td></tr></table>", "| ab |\n| --- |\n"),
        (
            "<table><tr><td>x<table><tr><td>in</td></tr></table>y</td><td>z</td></tr></table>",
            "| x in y | z |\n| --- | --- |\n",
        ),
        (
            "<table><tr><td><h3>H</h3></td><td><pre>code</pre></td></tr></table>",
            "| H | code |\n| --- | --- |\n",
        ),
        ("<table><caption>Limits</caption><tr><td>1</td></tr></table>", "Limits\n| 1 |\n| --- |\n"),
        ("<table><tr></tr></table><p>x</p>", "x\n"),
        ("<table><tr><td>open", "| open |\n| --- |\n"),
        # code
        (
            "<p>Run:</p><pre>\nif x:\n    go()\n</pre><p>Done.</p>",
            "Run:\n\n```\nif x:\n    go()\n```\n\nDone.\n",
        ),
        ("<pre>a\n\n\n\nb</pre>", "```\na\n\n\n\nb\n```\n"),
        ("<pre>x<p>after", "```\nx\n\nafter\n```\n"),
        ("<p>```</p><p>  spaced  </p>", "```\n\nspaced\n"),
        # what is dropped, and a head left open
        ("<head><title>T</title><style>p {}</style></head><p>Kept.</p><script>var x;</script>", "Kept.\n"),
        ("<html><head><title>T</title><body><h1>Title</h1><p>Body</p>", "# Title\n\nBody\n"),
        ("<title>Only a title</title><noscript>enable js</noscript><p>Body</p>", "Body\n"),
        # The main content alone when the page marks it; navigation always dropped.
        (
            "<nav>Home | Docs</nav><main><h1>T</h1><p>Body</p></main><footer>(c) site</footer>",
            "# T\n\nBody\n",
        ),
        (
            '<div>menu</div><div role="main"><div><p>one</p></div><p>two</p></div><div>footer</div>',
            "one\n\ntwo\n",
        ),
        ("<p>Text</p><aside>Related pages</aside><nav><ul><li>a</li></ul></nav>", "Text\n"),
        ("<p>outside</p><main> </main>", "outside\n"),
        ("<main><p>first</p></main><p>between</p><main><p>second</p></main>", "first\n\nsecond\n"),
        # stray end tags, empty input
        ("</pre></tr></script></table><td>cell</td><p>ok</p>", "cell\n\nok\n"),
        ("", ""),
    ],
)
def test_html_to_text(html: str, text: str) -> None:
    assert html_to_text(html) == text
