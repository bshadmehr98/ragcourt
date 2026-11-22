"""Headings, tables and code blocks (design §5.1)."""

from ragcourt.core.structure import structure_of

TEXT = """# Title

Intro line
==========

Para.

| a | b |
| - | - |
| 1 | 2 |

| lone row |

```python
# not a heading
| not | a table |
```

    indented code
    more code

After.
Under
---
~~~
unclosed"""


def spans(text: str, found: tuple[tuple[int, int], ...]) -> list[str]:
    return [text[start:end] for start, end in found]


def test_structure() -> None:
    structure = structure_of(TEXT)
    assert spans(TEXT, structure.headings) == ["# Title", "Intro line\n==========", "Under\n---"]
    assert spans(TEXT, structure.tables) == ["| a | b |\n| - | - |\n| 1 | 2 |"]
    code = spans(TEXT, structure.code_blocks)
    assert code[0].startswith("```python") and code[0].endswith("```")
    assert code[1] == "    indented code\n    more code"
    assert code[2] == "~~~\nunclosed"


def test_plain_text_has_no_structure() -> None:
    structure = structure_of("just words\nand more")
    assert structure.headings == structure.tables == structure.code_blocks == ()
