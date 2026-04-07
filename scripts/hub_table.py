"""Build the hub comparison DataFrame for community/hubs.qmd."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml

CATEGORIES: dict[str, str] = {
    "uscdc":             "Active",
    "smhct":             "Active",
    "epiengage":         "Active",
    "ai4casting":        "Active",
    "ecdc":              "Active",
    "cadph":             "Active",
    "accidda":           "Active",
    "acefa":             "Active",
    "dailypartita":      "Active",
    "hubverse":          "Archival",
    "ecdc-archival":     "Archival",
    "hopkinsidd":        "Archival",
    "reichlab-training": "Training",
    "sjfox":             "Training",
    "reichlab-modeldev": "Model Development",
}


def resource_link(url: str | None, label: str = "") -> str:
    """Return a linked checkmark (✓) if url is provided, or empty string.

    Uses Unicode rather than web-font icons so the symbol renders reliably
    regardless of whether FontAwesome CSS is loaded.
    """
    if not url:
        return ""
    return f'<a href="{url}" target="_blank" title="{label}" class="text-success fw-bold">✓</a>'


def build_hub_dataframe(path: Path) -> pd.DataFrame:
    """Parse hub YAML frontmatter and return a comparison DataFrame."""
    content = path.read_text(encoding="utf-8")
    yaml_text = re.match(r"^---\n(.*?)\n---", content, re.DOTALL).group(1)
    hubs_data = yaml.safe_load(yaml_text)["hubs"]

    rows = []
    for org_key, org in hubs_data.items():
        if org_key == "example":
            continue
        for hub in org.get("hubs", []):
            repo = hub.get("repo")
            rows.append(
                {
                    "Hub": hub["name"],
                    "Organization": org["name"],
                    "Category": CATEGORIES.get(org_key, "Other"),
                    "Models": hub.get("count"),
                    "Repo": (
                        f'<a href="https://github.com/{repo}" target="_blank"'
                        f' class="font-monospace small">{repo}</a>'
                        if repo
                        else '<span class="text-muted fst-italic">private</span>'
                    ),
                    "Open Data": (
                        resource_link(
                            "https://hubverse-org.github.io/hubData/articles/connect_hub.html",
                            f"s3://{hub['aws']}",
                        )
                        if hub.get("aws")
                        else ""
                    ),
                    "Insights":    resource_link(hub.get("insights"),  "Insights"),
                    "Forecasts":   resource_link(hub.get("forecasts"), "Forecasts"),
                    "Evaluations": resource_link(hub.get("evals"),     "Evaluations"),
                }
            )

    return pd.DataFrame(rows)
