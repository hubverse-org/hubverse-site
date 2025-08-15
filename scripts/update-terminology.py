import requests
import re

# Source URLs
ABBR_URL = "https://raw.githubusercontent.com/hubverse-org/hubDocs/main/docs/source/overview/abbreviations.md"
DEFS_URL = "https://raw.githubusercontent.com/hubverse-org/hubDocs/main/docs/source/overview/terminology.md"
MODEL_TASKS_URL = "https://docs.hubverse.io/en/latest/user-guide/tasks.html"
DEST_FILE = "terminology.qmd"

def fetch_markdown(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

def process_definitions(md):
    # Remove the top-level header
    md = re.sub(r"^# Terminology\s*", "", md, flags=re.MULTILINE)

    # 1. Transform "Modeling Tasks Terminology" section
    md = re.sub(
        r"\(model-tasks\)=\s*## Modeling Tasks Terminology\s*\n\[.*?Learn more about modeling tasks.*?\]\(.*?\)\s*",
        f"## Modeling Tasks Terminology {{#model-tasks}}\n\n[{{< fa book >}} Learn more about modeling tasks]({MODEL_TASKS_URL}){{.btn .btn-outline-dark .ms-auto}}\n\n",
        md,
        flags=re.DOTALL
    )

    # 2. Transform "Prediction Terminology" section and figure block
    def pred_term_repl(match):
        alt_text = (
            "Figure illustrating the difference between nowcasts, forecasts, and projections showing a timeline of weekly incident case counts from February 2020 to early March 2021 with projections from April to September 2021. "
            "The range from the graph's beginning to March 2021 is labeled \"Surveillance Data.\" "
            "The \"Nowcast\" range covers three weeks of preliminary surveillance and projected data with confidence intervals. "
            "The \"Forecast\" range has no observed data and covers the next four weeks with four slightly diverging model estimates and confidence intervals. "
            "The \"Projections\" range covers the period between May 2021 and September 2021 and shows the models' confidence intervals."
        )
        # Add two newlines to ensure the next admonition is separated
        return (
            "## Prediction Terminology {#prediction-terms}\n\n"
            "![Figure credits: Alex Vespignani and Nicole Samay](/includes/img/horizon-nomenclature.png)"
            "{#horizons_nomenclature fig-alt='" + alt_text.replace("'", "\\'") + "'}\n\n"
        )

    md = re.sub(
        r"\(prediction-terms\)=\s*## Prediction Terminology\s*```{figure}.*?name: horizon-nomenclature.*?```",
        pred_term_repl,
        md,
        flags=re.DOTALL
    )

    # 3. Find all admonition blocks and convert to definition list format
    # Allow for optional whitespace or newlines before the block
    def_block_pattern = re.compile(
        r"\s*(\([^)]+\)=)?\s*```{admonition} ([^\n]+)\n(.*?)```",
        re.DOTALL | re.MULTILINE
    )

    def repl(match):
        anchor = match.group(1)
        if anchor:
            anchor = anchor.strip("()=")
            anchor_str = f"{{#{anchor}}}"
        else:
            anchor_str = ""
        term = match.group(2).strip()
        definition = match.group(3).strip()
        # Remove any trailing newlines
        definition = definition.replace("\n", " ").strip()
        # Fix internal links: change #def-model-output to #model-output, etc.
        definition = re.sub(r"\(#def-([^)]+)\)", r"(#\1)", definition)
        # Format as Quarto definition list
        return f"\n\n[{term}]{anchor_str}\n: {definition}\n"

    # Replace all admonition blocks
    md = def_block_pattern.sub(repl, md)

    # Remove any remaining Sphinx anchors (e.g., (team)=)
    md = re.sub(r"^\([^)]+\)=\s*", "", md, flags=re.MULTILINE)

    # Remove any remaining code block markers
    md = re.sub(r"```{admonition} [^\n]+\n", "", md)
    md = re.sub(r"```", "", md)

    # Clean up excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)

    return md.strip()

def main():
    # Fetch both markdown files
    abbr_md = fetch_markdown(ABBR_URL)
    defs_md = fetch_markdown(DEFS_URL)

    # Process definitions
    defs_md = process_definitions(defs_md)

    # Add Quarto YAML header
    header = """---
title: "Terminology"
---

<!--
This page should not be edited directly as it is automatically regenerated with `scripts/update-terminology.py`
The content is drawn from these two sites:
https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/terminology.md
https://github.com/hubverse-org/hubDocs/blob/main/docs/source/overview/abbreviations.md
Any edits to concepts, terms or abbreviations should be made on the hubDocs repository.
-->
"""


    # Compose final content
    final_md = f"{header}\n{defs_md}\n\n\n{abbr_md}"

    # Save to file
    with open(DEST_FILE, "w", encoding="utf-8") as f:
        f.write(final_md)

if __name__ == "__main__":
    main()

