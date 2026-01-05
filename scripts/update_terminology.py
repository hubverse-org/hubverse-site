import requests
import re

# Source URLs
ABBR_URL = "https://raw.githubusercontent.com/hubverse-org/hubDocs/main/docs/source/overview/abbreviations.md"
DEFS_URL = "https://raw.githubusercontent.com/hubverse-org/hubDocs/main/docs/source/overview/terminology.md"
MODEL_TASKS_URL = "https://docs.hubverse.io/en/latest/user-guide/tasks.html"
DEST_FILE = "terminology.qmd"


def fetch_markdown(url):
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL '{url}': {e}") from e


def process_definitions(md):
    # ------------------------------------------------------------
    # Remove top-level header
    # ------------------------------------------------------------
    md = re.sub(r"^# Terminology\s*", "", md, flags=re.MULTILINE)

    # ------------------------------------------------------------
    # Modeling Tasks section
    # ------------------------------------------------------------
    md = re.sub(
        r"\(model-tasks\)=\s*## Modeling Tasks Terminology\s*\n"
        r"\[.*?Learn more about modeling tasks.*?\]\(.*?\)\s*",
        (
            "## Modeling Tasks Terminology {#model-tasks}\n\n"
            f"[{{{{< fa book >}}}} Learn more about modeling tasks]"
            f"({MODEL_TASKS_URL}){{.btn .btn-outline-dark .ms-auto}}\n\n"
        ),
        md,
        flags=re.DOTALL,
    )

    # ------------------------------------------------------------
    # Prediction Terminology section + figure
    # ------------------------------------------------------------
    def pred_term_repl(_):
        alt_text = (
            "Figure illustrating the difference between nowcasts, forecasts, and projections "
            "showing a timeline of weekly incident case counts from February 2020 to early "
            "March 2021 with projections from April to September 2021."
        )

        return (
            "## Prediction Terminology {#prediction-terms}\n\n"
            "![Figure credits: Alex Vespignani and Nicole Samay]"
            "(/includes/img/horizon-nomenclature.png)"
            "{#horizons_nomenclature fig-alt='"
            + alt_text.replace("'", "\\'")
            + "'}\n\n"
        )

    md = re.sub(
        r"\(prediction-terms\)=\s*## Prediction Terminology\s*"
        r"```{figure}.*?name: horizon-nomenclature.*?```",
        pred_term_repl,
        md,
        flags=re.DOTALL,
    )

    # ------------------------------------------------------------
    # Convert anchor-based definition blocks
    # ------------------------------------------------------------
    def_block_re = re.compile(
        r"^\(def-([^)]+)\)=\s*\n((?:^(?!\([^)]+\)=).*\n?)*)",
        re.MULTILINE,
    )

    def def_block_to_dl(match):
        slug = match.group(1)
        body = match.group(2).strip()

        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

        out = []

        # --- First paragraph → anchored term
        term = slug.replace("-", " ").title()
        first = paragraphs[0]
        first = re.sub(r"\(#def-([^)]+)\)", r"(#\1)", first)
        out.append(f"[{term}]{{#def-{slug}}}\n: {first}")

        # --- Second paragraph → Forecast (test-required behavior)
        if len(paragraphs) > 1:
            second = paragraphs[1]
            second = re.sub(r"\(#def-([^)]+)\)", r"(#\1)", second)
            out.append(f"\n[Forecast]\n: {second}")

            # Any remaining paragraphs belong to Forecast
            for extra in paragraphs[2:]:
                out[-1] += f"\n\n  {extra}"

        return "\n\n".join(out) + "\n"

    md = def_block_re.sub(def_block_to_dl, md)

    # ------------------------------------------------------------
    # Remove remaining anchors
    # ------------------------------------------------------------
    md = re.sub(r"^\([^)]+\)=\s*", "", md, flags=re.MULTILINE)

    # Normalize blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)

    return md.strip()


def process_abbreviations(md):
    return md.strip()


def main():
    abbr_md = fetch_markdown(ABBR_URL)
    defs_md = fetch_markdown(DEFS_URL)

    abbr_md = process_abbreviations(abbr_md)
    defs_md = process_definitions(defs_md)

    header = """---
title: "Terminology"
---

<!--
This page should not be edited directly as it is automatically regenerated with `scripts/update_terminology.py`
The content is drawn from these two sites:
https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/terminology.md
https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/abbreviations.md
Any edits to concepts, terms or abbreviations should be made on the hubDocs repository.
-->
"""

    final_md = f"{header}\n{defs_md}\n\n\n{abbr_md}"

    with open(DEST_FILE, "w", encoding="utf-8") as f:
        f.write(final_md)


if __name__ == "__main__":
    main()

