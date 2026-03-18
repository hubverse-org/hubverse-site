import json
from pathlib import Path

from scripts.print_hub_list import build_hub_table
from scripts.print_hub_list import parse_args
from scripts.print_hub_list import parse_repo_slug
from scripts.print_hub_list import write_csv
from scripts.print_hub_list import write_hubs_json
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


# ---------------------------------------------------------------------------
# parse_repo_slug
# ---------------------------------------------------------------------------


def test_parse_repo_slug_simple():
    result = parse_repo_slug("cdcepi/FluSight-forecast-hub")
    assert result == {"org": "cdcepi", "repo": "FluSight-forecast-hub"}


def test_parse_repo_slug_with_subdir():
    result = parse_repo_slug("reichlab/flusion/tree/main/retrospective-hub")
    assert result == {
        "org": "reichlab",
        "repo": "flusion",
        "hub_subdir": "retrospective-hub",
    }


def test_parse_repo_slug_without_subdir_has_no_hub_subdir_key():
    result = parse_repo_slug("ai4castinghub/hospitalization-forecast")
    assert "hub_subdir" not in result


# ---------------------------------------------------------------------------
# build_hub_table – sort order
# ---------------------------------------------------------------------------


def test_build_hub_table_sorts_case_insensitively(tmp_path):
    """CDCgov (uppercase) must come after ai4castinghub (lowercase) when
    sorting is case-insensitive."""
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """---
hubs:
  uscdc:
    name: "CDC"
    hubs:
      - name: "COVID-19 Forecast Hub"
        repo: CDCgov/covid19-forecast-hub
  ai4casting:
    name: "AI4Casting"
    hubs:
      - name: "Hospitalization Forecast Hub"
        repo: ai4castinghub/hospitalization-forecast
---
""",
        encoding="utf-8",
    )

    rows = build_hub_table(qmd)

    assert rows[0]["repo"] == "ai4castinghub/hospitalization-forecast"
    assert rows[1]["repo"] == "CDCgov/covid19-forecast-hub"


def test_build_hub_table_sorts_no_repo_hubs_by_hub_name(tmp_path):
    """Hubs without a repo slug should be sorted by their hub name."""
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """---
hubs:
  orgz:
    name: "Org Z"
    hubs:
      - name: "Zebra Hub"
  orga:
    name: "Org A"
    hubs:
      - name: "Apple Hub"
---
""",
        encoding="utf-8",
    )

    rows = build_hub_table(qmd)

    assert rows[0]["hub name"] == "Apple Hub"
    assert rows[1]["hub name"] == "Zebra Hub"


def test_build_hub_table_mixes_repo_and_no_repo_alphabetically(tmp_path):
    """Rows with and without repos should be interleaved by their effective sort key."""
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """---
hubs:
  orga:
    name: "Org A"
    hubs:
      - name: "Mango Hub"
        repo: zorg/z-repo
      - name: "Apple Hub"
---
""",
        encoding="utf-8",
    )

    rows = build_hub_table(qmd)

    # "Apple Hub" (no repo, key="apple hub") sorts before "zorg/z-repo" (key="zorg/z-repo")
    assert rows[0]["hub name"] == "Apple Hub"
    assert rows[1]["repo"] == "zorg/z-repo"


# ---------------------------------------------------------------------------
# write_hubs_json
# ---------------------------------------------------------------------------


def test_write_hubs_json_creates_file(tmp_path):
    output = tmp_path / "hubs.json"
    rows = [{"repo": "cdcepi/FluSight-forecast-hub", "hub name": "", "name": "", "example": "", "insights": "", "aws": ""}]

    write_hubs_json(rows, output)

    assert output.exists()


def test_write_hubs_json_content(tmp_path):
    output = tmp_path / "hubs.json"
    rows = [
        {"repo": "ai4castinghub/hospitalization-forecast", "hub name": "", "name": "", "example": "", "insights": "", "aws": ""},
        {"repo": "cdcepi/FluSight-forecast-hub", "hub name": "", "name": "", "example": "", "insights": "", "aws": ""},
    ]

    write_hubs_json(rows, output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == {
        "hubs": [
            {"org": "ai4castinghub", "repo": "hospitalization-forecast"},
            {"org": "cdcepi", "repo": "FluSight-forecast-hub"},
        ]
    }


def test_write_hubs_json_includes_hub_subdir(tmp_path):
    output = tmp_path / "hubs.json"
    rows = [
        {"repo": "reichlab/flusion/tree/main/retrospective-hub", "hub name": "", "name": "", "example": "", "insights": "", "aws": ""},
    ]

    write_hubs_json(rows, output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["hubs"][0] == {
        "org": "reichlab",
        "repo": "flusion",
        "hub_subdir": "retrospective-hub",
    }


def test_write_hubs_json_skips_rows_without_repo(tmp_path):
    output = tmp_path / "hubs.json"
    rows = [
        {"repo": "", "hub name": "No Repo Hub", "name": "", "example": "", "insights": "", "aws": ""},
        {"repo": "cdcepi/FluSight-forecast-hub", "hub name": "", "name": "", "example": "", "insights": "", "aws": ""},
    ]

    write_hubs_json(rows, output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert len(data["hubs"]) == 1
    assert data["hubs"][0]["org"] == "cdcepi"


def test_write_hubs_json_each_hub_on_one_line(tmp_path):
    """Each hub entry must be a single line (compact JSON object)."""
    output = tmp_path / "hubs.json"
    rows = [
        {"repo": "ai4castinghub/hospitalization-forecast", "hub name": "", "name": "", "example": "", "insights": "", "aws": ""},
        {"repo": "cdcepi/FluSight-forecast-hub", "hub name": "", "name": "", "example": "", "insights": "", "aws": ""},
    ]

    write_hubs_json(rows, output)

    lines = output.read_text(encoding="utf-8").splitlines()
    hub_lines = [l.strip().rstrip(",") for l in lines if l.strip().startswith('{"')]
    for line in hub_lines:
        assert json.loads(line)  # each line must be valid JSON on its own


# ---------------------------------------------------------------------------
# parse_args – defaults and new flags
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    args = parse_args([])
    assert args.write_csv is True
    assert args.write_md is False
    assert args.write_json is True


def test_parse_args_write_md_flag():
    args = parse_args(["--write-md"])
    assert args.write_md is True


def test_parse_args_no_csv_flag():
    args = parse_args(["--no-csv"])
    assert args.write_csv is False


def test_parse_args_no_json_flag():
    args = parse_args(["--no-json"])
    assert args.write_json is False


