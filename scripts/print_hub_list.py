import argparse
import csv
import json
from pathlib import Path

import yaml


HEADERS = ["example", "name", "hub name", "repo", "insights", "aws"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate hub tables from active-hubs.qmd"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write generated files. Defaults to the project output/ directory.",
    )
    parser.add_argument(
        "--no-csv",
        dest="write_csv",
        action="store_false",
        help="Do not write CSV output.",
    )
    parser.add_argument(
        "--write-md",
        dest="write_md",
        action="store_true",
        help="Write Markdown output (disabled by default).",
    )
    parser.add_argument(
        "--no-json",
        dest="write_json",
        action="store_false",
        help="Do not write hubs.json output.",
    )
    parser.set_defaults(write_csv=True, write_md=False, write_json=True)
    return parser.parse_args(argv)


def parse_repo_slug(slug):
    """Parse an org/repo slug (possibly with /tree/main/subdir) into a dict.

    Examples
    --------
    "cdcepi/FluSight-forecast-hub"
        -> {"org": "cdcepi", "repo": "FluSight-forecast-hub"}
    "reichlab/flusion/tree/main/retrospective-hub"
        -> {"org": "reichlab", "repo": "flusion", "hub_subdir": "retrospective-hub"}
    """
    parts = slug.split("/")
    entry = {"org": parts[0], "repo": parts[1]}
    # Handle e.g. "org/repo/tree/main/subdir"
    if len(parts) >= 5 and parts[2] == "tree":
        entry["hub_subdir"] = parts[4]
    return entry


def build_hub_table(input_qmd: Path):
    """Parse a Quarto file and return a list of hub rows sorted by repo slug."""
    with open(input_qmd, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))

    data = docs[0]  # Quarto front matter
    rows = []

    for org_slug, org_data in (data.get("hubs") or {}).items():
        # Drop example / placeholder org
        if org_slug == "example":
            continue

        org_name = org_data.get("name", "")

        for hub in (org_data.get("hubs") or []):
            rows.append(
                {
                    "example": org_slug,
                    "name": org_name,
                    "hub name": hub.get("name", ""),
                    "repo": hub.get("repo", ""),
                    "insights": hub.get("insights", ""),
                    "aws": hub.get("aws", ""),
                    "archived_dirs": hub.get("archived_dirs") or [],
                }
            )

    rows.sort(key=lambda r: (r["repo"] or r["hub name"]).lower())
    return rows


def write_csv(rows, output_csv: Path):
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows, output_md: Path):
    with open(output_md, "w", encoding="utf-8") as f:
        # header
        f.write("| " + " | ".join(HEADERS) + " |\n")
        f.write("| " + " | ".join("-" * len(h) for h in HEADERS) + " |\n")

        # rows
        for r in rows:
            f.write("| " + " | ".join(str(r[h]) for h in HEADERS) + " |\n")


def write_hubs_json(rows, output_json: Path):
    """Write hubs.json with {org, repo[, hub_subdir][, archived_dirs]} entries for hubs that have a repo slug."""
    hubs = []
    for r in rows:
        if not r.get("repo", "").strip():
            continue
        entry = parse_repo_slug(r["repo"])
        if r.get("archived_dirs"):
            entry["archived_dirs"] = r["archived_dirs"]
        hubs.append(entry)
    hub_lines = ",\n".join(f"    {json.dumps(h)}" for h in hubs)
    with open(output_json, "w", encoding="utf-8") as f:
        f.write(f'{{\n  "hubs": [\n{hub_lines}\n  ]\n}}\n')


def main(argv=None):
    base_dir = Path(__file__).resolve().parents[1]
    args = parse_args(argv)

    input_qmd = base_dir / "_data" / "active-hubs.qmd"
    output_dir = args.output_dir or (base_dir / "output")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / "active-hubs-table.csv"
    output_md = output_dir / "active-hubs-table.md"
    output_json = output_dir / "hubs.json"

    rows = build_hub_table(input_qmd)

    if args.write_csv:
        write_csv(rows, output_csv)

    # Markdown output is disabled by default; pass --write-md to enable.
    # if args.write_md:
    #     write_markdown(rows, output_md)

    if args.write_json:
        write_hubs_json(rows, output_json)

    print(f"Saved {len(rows)} rows to {output_dir}")


if __name__ == "__main__":
    main()

