"""Build the hub comparison DataFrame for community/hubs.qmd."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml


def canon_repo_key(repo_slug: str) -> str:
    """Normalize a repo slug to the form used in hub_stats_summary.csv.

    Converts 'org/repo/tree/main/subdir' -> 'org/repo/subdir'.
    Plain 'org/repo' slugs are returned unchanged.
    """
    parts = repo_slug.split("/")
    if len(parts) >= 5 and parts[2] == "tree":
        return f"{parts[0]}/{parts[1]}/{parts[4]}"
    return "/".join(parts[:2])


def load_hub_row_counts(path: Path) -> dict[str, int]:
    """Read hub_stats_summary.csv and return total row counts per hub.

    Sums model-output and target-data rows for each hub.
    Returns an empty dict if the file does not exist.
    """
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df = df[df["dir"].isin(["model-output", "target-data"])]
    return dict(df.groupby("repo")["row_count"].sum().astype(int))

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
                    "RepoSlug": repo or "",
                    "Repo": (
                        f'<a href="https://github.com/{repo}" target="_blank"'
                        f' class="font-monospace small">{repo}</a>'
                        if repo
                        else '<span class="text-muted fst-italic">private</span>'
                    ),
                    "S3 Bucket": (
                        f'<span class="text-success fw-bold" title="s3://{hub["aws"]}">✓</span>'
                        if hub.get("aws")
                        else ""
                    ),
                    "Insights":    resource_link(hub.get("insights"),  "Insights"),
                    "Forecasts":   resource_link(hub.get("forecasts"), "Forecasts"),
                    "Evaluations": resource_link(hub.get("evals"),     "Evaluations"),
                }
            )

    return pd.DataFrame(rows)
