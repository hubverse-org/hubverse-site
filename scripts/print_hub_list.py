import yaml
import csv
from pathlib import Path


HEADERS = ["example", "name", "hub name", "repo", "insights", "aws"]


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
            rows.append({
                "example": org_slug,
                "name": org_name,
                "hub name": hub.get("name", ""),
                "repo": hub.get("repo", ""),
                "insights": hub.get("insights", ""),
                "aws": hub.get("aws", ""),
            })

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


def main():
    base_dir = Path(__file__).resolve().parents[1]

    input_qmd = base_dir / "_data" / "active-hubs.qmd"
    output_csv = base_dir / "_data" / "active-hubs-table.csv"
    output_md = base_dir / "_data" / "active-hubs-table.md"

    WRITE_CSV = True
    WRITE_MD = True

    rows = build_hub_table(input_qmd)

    if WRITE_CSV:
        write_csv(rows, output_csv)

    if WRITE_MD:
        write_markdown(rows, output_md)

    print(f"Saved {len(rows)} rows")


if __name__ == "__main__":
    main()

