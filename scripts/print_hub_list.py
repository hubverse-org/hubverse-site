import argparse
import csv
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
        help="Directory to write generated files. Defaults to the project _data directory.",
    )
    parser.add_argument(
        "--no-csv",
        dest="write_csv",
        action="store_false",
        help="Do not write CSV output.",
    )
    parser.add_argument(
        "--no-md",
        dest="write_md",
        action="store_false",
        help="Do not write Markdown output.",
    )
    parser.set_defaults(write_csv=True, write_md=True)
    return parser.parse_args(argv)


def build_hub_table(input_qmd: Path):
    """Parse a Quarto file and return a list of hub rows."""
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
                }
            )

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


def main(argv=None):
    base_dir = Path(__file__).resolve().parents[1]
    args = parse_args(argv)

    input_qmd = base_dir / "_data" / "active-hubs.qmd"
    output_dir = args.output_dir or (base_dir / "_data")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / "active-hubs-table.csv"
    output_md = output_dir / "active-hubs-table.md"

    rows = build_hub_table(input_qmd)

    if args.write_csv:
        write_csv(rows, output_csv)

    if args.write_md:
        write_markdown(rows, output_md)

    print(f"Saved {len(rows)} rows to {output_dir}")


if __name__ == "__main__":
    main()

