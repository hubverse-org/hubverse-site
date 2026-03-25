import re
import requests

CITE_URL = "https://raw.githubusercontent.com/hubverse-org/hubDocs/main/docs/source/overview/cite.md"

DEST_FILE = "cite.qmd"


def fetch_markdown(url: str) -> str:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL '{url}': {e}") from e


def remove_top_header(md: str) -> str:
    return re.sub(
        r"^\s*#\s*How\s+to\s+cite\s*\n+",
        "",
        md,
        flags=re.IGNORECASE | re.MULTILINE,
    )


def convert_admonitions_to_callouts(md: str) -> str:
    """
    Convert fenced admonitions:

        ```{admonition} Title
        Body
        ```

    or

        ```{{admonition}} Title
        Body
        ```

    into Quarto callout-note blocks.
    """
    pattern = re.compile(
        r"```(?:\{\{admonition\}\}|\{admonition\})\s+([^\n]+)\n(.*?)\n```",
        flags=re.DOTALL,
    )

    def repl(m: re.Match) -> str:
        title = m.group(1).strip()
        body = m.group(2).strip()
        return (
            "\n\n"
            "::: {.callout-note}\n"
            f"## {title}\n\n"
            f"{body}\n"
            ":::\n"
        )

    return pattern.sub(repl, md)


# Ensures that any BibTeX code block is fenced as ```bibtex, while leaving all other fenced blocks unchanged.
def normalize_bibtex_fences(md: str) -> str:
    lines = md.splitlines()
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # If this is already a correctly labeled BibTeX code fence (```bibtex), copy the entire fenced block verbatim.
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

        # If there is a "BibTeX:" label followed by an unlabeled fenced block, convert the ``` fence into ```bibtex .
        if re.match(r"^\s*BibTeX:\s*$", line):
            out.append(line)
            if i + 1 < len(lines) and re.match(r"^\s*```\s*$", lines[i + 1]):
                out.append("```bibtex")
                i += 2
                while i < len(lines):
                    out.append(lines[i])
                    if re.match(r"^\s*```\s*$", lines[i]):
                        i += 1
                        break
                    i += 1
                continue
            i += 1
            continue

        # If there's any other fenced code block, pass it through unchanged (no relabeling)
        if re.match(r"^\s*```\s*$", line):
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
    return r"""---
title: "{{< fa quote-left >}} &nbsp;How to cite"
---

<!--
This page should not be edited directly as it is automatically regenerated with `scripts/update_cite.py`
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
    nav_block = (
        "\n\n"
        ":::: {.page-nav}\n"
        "::: {.prev-page}\n"
        "[‹](/trainings.md){.prev-arrow}\n\n"
        "[Previous](/trainings.md){.prev-label}\n\n"
        "[**Trainings**](/trainings.md){.prev-title}\n"
        ":::\n\n"
        "::: {.next-page}\n"
        "[Next](/CONTRIBUTING.md){.next-label}\n\n"
        "[›](/CONTRIBUTING.md){.next-arrow}\n\n"
        "[**Contributing to the site**](/CONTRIBUTING.md){.next-title}\n"
        ":::\n"
        "::::\n"
    )
    final_qmd = f"{build_header()}\n{body}{nav_block}"

    with open(DEST_FILE, "w", encoding="utf-8") as f:
        f.write(final_qmd)


if __name__ == "__main__":
    main()

