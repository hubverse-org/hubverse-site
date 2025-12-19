# scripts/update-cite.py

import re
import requests

# Source URLs
CITE_URL = "https://raw.githubusercontent.com/hubverse-org/hubDocs/main/docs/source/overview/cite.md"

# Destination file
DEST_FILE = "cite.qmd"


def fetch_markdown(url: str) -> str:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL '{url}': {e}") from e


def remove_top_header(md: str) -> str:
    # Remove leading "# How to cite" H1; YAML will provide title
    return re.sub(r"^\s*#\s*How\s+to\s+cite\s*\n+", "", md, flags=re.IGNORECASE | re.MULTILINE)


def convert_admonitions_to_callouts(md: str) -> str:
    # Convert ```{admonition} Title ... ``` to Quarto callout-note blocks
    pattern = re.compile(r"```{admonition}\s+([^\n]+)\n(.*?)\n```", flags=re.DOTALL)

    def repl(m: re.Match) -> str:
        title = m.group(1).strip()
        body = m.group(2).strip()
        return f"\n\n::: {{.callout-note}}\n## {title}\n\n{body}\n:::\n"

    return pattern.sub(repl, md)


def normalize_bibtex_fences(md: str) -> str:
    """
    Ensure BibTeX blocks use ```bibtex fences exactly:
    - If a fenced block already starts with ```bibtex, leave it.
    - If a fenced block appears immediately after a line containing 'BibTeX:', convert that fence to ```bibtex.
    - Otherwise leave other code fences unchanged.
    """

    lines = md.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect "BibTeX:" label line
        if re.match(r"^\s*BibTeX:\s*$", line):
            out.append(line)
            # Look ahead for a fence; convert to ```bibtex if present
            if i + 1 < len(lines) and re.match(r"^\s*```(\s*)$", lines[i + 1]):
                out.append("```bibtex")
                i += 2
                # Copy until closing ```
                while i < len(lines):
                    if re.match(r"^\s*```\s*$", lines[i]):
                        out.append("```")
                        i += 1
                        break
                    out.append(lines[i])
                    i += 1
                continue
            else:
                i += 1
                continue

        # If this is a generic fence, pass through, but don’t alter non-BibTeX blocks
        if re.match(r"^\s*```(\s*)$", line):
            # Peek to see if this block contains BibTeX-looking content (optional safeguard)
            # We’ll just pass it through unless it’s handled by the BibTeX: logic above.
            out.append(line)
            i += 1
            while i < len(lines):
                out.append(lines[i])
                if re.match(r"^\s*```\s*$", lines[i]):
                    i += 1
                    break
                i += 1
            continue

        # Already a bibtex fence → leave as-is and copy block
        if re.match(r"^\s*```bibtex\s*$", line):
            out.append(line)
            i += 1
            while i < len(lines):
                out.append(lines[i])
                if re.match(r"^\s*```\s*$", lines[i]):
                    i += 1
                    break
                i += 1
            continue

        out.append(line)
        i += 1

    return "\n".join(out)


def cleanup_blank_lines(md: str) -> str:
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def build_header() -> str:
    return """---
title: "How to cite"
---

<!--
This page should not be edited directly as it is automatically regenerated with `scripts/update-cite.py`
The content is drawn from this source:
https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/cite.md
Any edits to citation content should be made on the hubDocs repository.
-->
"""


def process_cite_markdown(md: str) -> str:
    md = remove_top_header(md)
    md = convert_admonitions_to_callouts(md)
    md = normalize_bibtex_fences(md)
    md = cleanup_blank_lines(md)
    return md


def main():
    src_md = fetch_markdown(CITE_URL)
    body = process_cite_markdown(src_md)
    final_qmd = f"{build_header()}\n{body}"
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        f.write(final_qmd)


if __name__ == "__main__":
    main()

