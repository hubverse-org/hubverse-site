from pathlib import Path
from scripts.print_hub_list import build_hub_table
from scripts.print_hub_list import write_csv
from scripts.print_hub_list import write_markdown


def test_build_hub_table_parses_hubs(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"

    qmd.write_text(
        """---
hubs:
  epiengage:
    name: "epiENGAGE"
    hubs:
      - name: "Variant Nowcast Hub"
        repo: reichlab/variant-nowcast-hub
        insights: https://reichlab.io/variant-nowcast-hub-dashboard/
        aws: covid-variant-nowcast-hub
---
Some markdown content here.
""",
        encoding="utf-8",
    )

    rows = build_hub_table(qmd)

    assert len(rows) == 1
    assert rows[0]["example"] == "epiengage"
    assert rows[0]["name"] == "epiENGAGE"
    assert rows[0]["hub name"] == "Variant Nowcast Hub"
    assert rows[0]["repo"] == "reichlab/variant-nowcast-hub"
    assert rows[0]["aws"] == "covid-variant-nowcast-hub"


def test_example_org_is_dropped(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"

    qmd.write_text(
        """---
hubs:
  example:
    name: "Example Organization"
    hubs:
      - name: "Name of Hub"
        repo: example-org/hub-name
  epiengage:
    name: "epiENGAGE"
    hubs:
      - name: "Variant Nowcast Hub"
        repo: reichlab/variant-nowcast-hub
---
""",
        encoding="utf-8",
    )

    rows = build_hub_table(qmd)

    assert len(rows) == 1
    assert rows[0]["example"] == "epiengage"


def test_org_without_hubs_is_ignored(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"

    qmd.write_text(
        """---
hubs:
  example:
    name: "Example Org"
  other:
    name: "Other Org"
    hubs: []
---
""",
        encoding="utf-8",
    )

    rows = build_hub_table(qmd)

    assert rows == []


def test_write_csv_creates_file(tmp_path):
    output = tmp_path / "hubs.csv"

    rows = [
        {
            "example": "epiengage",
            "name": "epiENGAGE",
            "hub name": "Variant Nowcast Hub",
            "repo": "reichlab/variant-nowcast-hub",
            "insights": "https://example.com",
            "aws": "bucket-name",
        }
    ]

    write_csv(rows, output)

    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "Variant Nowcast Hub" in text


def test_write_markdown(tmp_path):
    output = tmp_path / "hubs.md"

    rows = [
        {
            "example": "epiengage",
            "name": "epiENGAGE",
            "hub name": "Variant Nowcast Hub",
            "repo": "reichlab/variant-nowcast-hub",
            "insights": "https://example.com",
            "aws": "covid-variant-nowcast-hub",
        }
    ]

    write_markdown(rows, output)

    text = output.read_text(encoding="utf-8")

    assert "| example | name | hub name |" in text
    assert "Variant Nowcast Hub" in text


