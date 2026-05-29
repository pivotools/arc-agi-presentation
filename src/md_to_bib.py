#!/usr/bin/env python3
"""
Parse 80_references.md (lines of the form [N] [Title](url)) and generate references.bib.
Usage: python md_to_bib.py [input.md] [output.bib]
Defaults: blog/posts/agentic_coding_arc_agi/text/80_references.md -> .../references.bib
"""
import re
import sys
from pathlib import Path

# Default paths relative to blog directory (parent of src/)
BLOG_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = BLOG_DIR / "posts" / "agentic_coding_arc_agi" / "text" / "80_references.md"
DEFAULT_OUTPUT = BLOG_DIR / "posts" / "agentic_coding_arc_agi" / "text" / "references.bib"

# Line format: [N] [Title](url)
# Uses greedy .+ for title to handle special chars like %, ], etc.
LINE_PATTERN = re.compile(r"^\[(\d+)\]\s+\[(.+)\]\((https?://[^\s)]+)\)\s*$")


def bibtex_escape(s: str) -> str:
    """Escape title for BibTeX: wrap in braces, double any internal braces."""
    return "{" + s.replace("{", "{{").replace("}", "}}") + "}"


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    input_path = input_path.resolve()
    output_path = output_path.resolve()

    entries = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE_PATTERN.match(line)
        if not m:
            continue
        num, title, url = m.groups()
        key = f"ref{num}"
        title_escaped = bibtex_escape(title)
        entries.append(
            f"""@misc{{{key},
  title = {title_escaped},
  url = {{{url}}}
}}"""
        )

    output_path.write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
