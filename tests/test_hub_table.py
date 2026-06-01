import textwrap
from pathlib import Path

import pandas as pd
import pytest

from scripts.hub_table import (
    CATEGORIES,
    build_hub_dataframe,
    canon_repo_key,
    load_hub_row_counts,
    resource_link,
)


# ---------------------------------------------------------------------------
# resource_link
# ---------------------------------------------------------------------------


def test_resource_link_returns_empty_string_for_none():
    assert resource_link(None) == ""


def test_resource_link_returns_empty_string_for_empty_string():
    assert resource_link("") == ""


def test_resource_link_contains_href():
    result = resource_link("https://example.com", "Forecasts")
    assert 'href="https://example.com"' in result


def test_resource_link_contains_checkmark():
    result = resource_link("https://example.com", "Forecasts")
    assert "✓" in result


def test_resource_link_contains_label_as_title():
    result = resource_link("https://example.com", "Forecasts")
    assert 'title="Forecasts"' in result


def test_resource_link_opens_in_new_tab():
    result = resource_link("https://example.com")
    assert 'target="_blank"' in result


# ---------------------------------------------------------------------------
# build_hub_dataframe – basic structure
# ---------------------------------------------------------------------------

MINIMAL_QMD = """\
---
hubs:
  epiengage:
    name: "epiENGAGE"
    hubs:
      - name: "Variant Nowcast Hub"
        repo: reichlab/variant-nowcast-hub
        license: MIT License
        count: 10
        aws: covid-variant-nowcast-hub
        insights: https://reichlab.io/variant-nowcast-hub-dashboard/
        forecasts: https://example.com/forecasts
        evals: https://example.com/evals
---
"""


@pytest.fixture
def minimal_qmd(tmp_path):
    p = tmp_path / "active-hubs.qmd"
    p.write_text(MINIMAL_QMD, encoding="utf-8")
    return p


def test_build_hub_dataframe_returns_expected_columns(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert list(df.columns) == [
        "Hub", "Organization", "Category", "Models",
        "RepoSlug", "Repo", "S3 Bucket", "Insights", "Forecasts", "Evaluations",
    ]


def test_build_hub_dataframe_hub_name(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert df.iloc[0]["Hub"] == "Variant Nowcast Hub"


def test_build_hub_dataframe_organization(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert df.iloc[0]["Organization"] == "epiENGAGE"


def test_build_hub_dataframe_models_count(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert df.iloc[0]["Models"] == 10


# ---------------------------------------------------------------------------
# build_hub_dataframe – example org is excluded
# ---------------------------------------------------------------------------


def test_example_org_is_excluded(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
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

    df = build_hub_dataframe(qmd)

    assert len(df) == 1
    assert df.iloc[0]["Hub"] == "Variant Nowcast Hub"


# ---------------------------------------------------------------------------
# build_hub_dataframe – category assignment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("org_key,expected_category", CATEGORIES.items())
def test_category_assignment(tmp_path, org_key, expected_category):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        f"""\
---
hubs:
  {org_key}:
    name: "Test Org"
    hubs:
      - name: "Test Hub"
---
""",
        encoding="utf-8",
    )

    df = build_hub_dataframe(qmd)

    assert df.iloc[0]["Category"] == expected_category


def test_unknown_org_key_gets_other_category(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  unknown-org:
    name: "Unknown Org"
    hubs:
      - name: "Some Hub"
---
""",
        encoding="utf-8",
    )

    df = build_hub_dataframe(qmd)

    assert df.iloc[0]["Category"] == "Other"


# ---------------------------------------------------------------------------
# build_hub_dataframe – Repo column
# ---------------------------------------------------------------------------


def test_public_hub_repo_contains_github_link(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  uscdc:
    name: "US CDC"
    hubs:
      - name: "FluSight"
        repo: cdcepi/FluSight-forecast-hub
---
""",
        encoding="utf-8",
    )

    df = build_hub_dataframe(qmd)

    assert "https://github.com/cdcepi/FluSight-forecast-hub" in df.iloc[0]["Repo"]


def test_private_hub_repo_contains_private_text(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  uscdc:
    name: "US CDC"
    hubs:
      - name: "Paraguay Forecast Hub"
---
""",
        encoding="utf-8",
    )

    df = build_hub_dataframe(qmd)

    assert "private" in df.iloc[0]["Repo"]


# ---------------------------------------------------------------------------
# build_hub_dataframe – optional resource columns
# ---------------------------------------------------------------------------


def test_missing_aws_produces_empty_open_data(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  uscdc:
    name: "US CDC"
    hubs:
      - name: "No Data Hub"
        repo: cdcepi/no-data-hub
---
""",
        encoding="utf-8",
    )

    df = build_hub_dataframe(qmd)

    assert df.iloc[0]["S3 Bucket"] == ""


def test_present_aws_produces_resource_link(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert "✓" in df.iloc[0]["S3 Bucket"]


def test_present_aws_resource_link_includes_bucket_name_in_title(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert "covid-variant-nowcast-hub" in df.iloc[0]["S3 Bucket"]


def test_missing_insights_produces_empty_string(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  uscdc:
    name: "US CDC"
    hubs:
      - name: "No Insights Hub"
---
""",
        encoding="utf-8",
    )
    df = build_hub_dataframe(qmd)
    assert df.iloc[0]["Insights"] == ""


def test_present_insights_produces_checkmark(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert "✓" in df.iloc[0]["Insights"]


def test_missing_count_produces_none_models(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  uscdc:
    name: "US CDC"
    hubs:
      - name: "No Count Hub"
---
""",
        encoding="utf-8",
    )
    df = build_hub_dataframe(qmd)
    assert df.iloc[0]["Models"] is None


# ---------------------------------------------------------------------------
# build_hub_dataframe – RepoSlug column
# ---------------------------------------------------------------------------


def test_reposlug_is_raw_slug(minimal_qmd):
    df = build_hub_dataframe(minimal_qmd)
    assert df.iloc[0]["RepoSlug"] == "reichlab/variant-nowcast-hub"


def test_reposlug_is_empty_string_for_private_hub(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  uscdc:
    name: "US CDC"
    hubs:
      - name: "Private Hub"
---
""",
        encoding="utf-8",
    )
    df = build_hub_dataframe(qmd)
    assert df.iloc[0]["RepoSlug"] == ""


def test_reposlug_preserves_subdir_slug(tmp_path):
    qmd = tmp_path / "active-hubs.qmd"
    qmd.write_text(
        """\
---
hubs:
  reichlab:
    name: "Reich Lab"
    hubs:
      - name: "Flusion Retro"
        repo: reichlab/flusion/tree/main/retrospective-hub
---
""",
        encoding="utf-8",
    )
    df = build_hub_dataframe(qmd)
    assert df.iloc[0]["RepoSlug"] == "reichlab/flusion/tree/main/retrospective-hub"


# ---------------------------------------------------------------------------
# canon_repo_key
# ---------------------------------------------------------------------------


def test_canon_repo_key_plain_slug():
    assert canon_repo_key("cdcepi/FluSight-forecast-hub") == "cdcepi/FluSight-forecast-hub"


def test_canon_repo_key_with_tree_subdir():
    result = canon_repo_key("reichlab/flusion/tree/main/retrospective-hub")
    assert result == "reichlab/flusion/retrospective-hub"


def test_canon_repo_key_ignores_extra_path_without_tree():
    assert canon_repo_key("org/repo") == "org/repo"


# ---------------------------------------------------------------------------
# load_hub_row_counts
# ---------------------------------------------------------------------------


def test_load_hub_row_counts_returns_empty_dict_if_file_missing(tmp_path):
    result = load_hub_row_counts(tmp_path / "nonexistent.csv")
    assert result == {}


def test_load_hub_row_counts_sums_model_output_and_target_data(tmp_path):
    csv_path = tmp_path / "summary.csv"
    csv_path.write_text(
        "repo,dir,row_count\n"
        "cdcepi/FluSight-forecast-hub,model-output,1000\n"
        "cdcepi/FluSight-forecast-hub,target-data,200\n",
        encoding="utf-8",
    )
    result = load_hub_row_counts(csv_path)
    assert result["cdcepi/FluSight-forecast-hub"] == 1200


def test_load_hub_row_counts_ignores_other_dirs(tmp_path):
    csv_path = tmp_path / "summary.csv"
    csv_path.write_text(
        "repo,dir,row_count\n"
        "org/repo,model-output,500\n"
        "org/repo,other-dir,9999\n",
        encoding="utf-8",
    )
    result = load_hub_row_counts(csv_path)
    assert result["org/repo"] == 500


def test_load_hub_row_counts_handles_multiple_hubs(tmp_path):
    csv_path = tmp_path / "summary.csv"
    csv_path.write_text(
        "repo,dir,row_count\n"
        "org/hub-a,model-output,100\n"
        "org/hub-b,target-data,200\n",
        encoding="utf-8",
    )
    result = load_hub_row_counts(csv_path)
    assert result == {"org/hub-a": 100, "org/hub-b": 200}


def test_load_hub_row_counts_only_one_dir_present(tmp_path):
    csv_path = tmp_path / "summary.csv"
    csv_path.write_text(
        "repo,dir,row_count\n"
        "org/repo,model-output,750\n",
        encoding="utf-8",
    )
    result = load_hub_row_counts(csv_path)
    assert result["org/repo"] == 750


# ---------------------------------------------------------------------------
# canon_repo_key + load_hub_row_counts integration
# (mirrors the lookup logic embedded in community/hubs.qmd)
# ---------------------------------------------------------------------------


def test_subdir_slug_lookup_via_canon_key(tmp_path):
    """A hub with a /tree/main/subdir slug should look up correctly."""
    csv_path = tmp_path / "summary.csv"
    csv_path.write_text(
        "repo,dir,row_count\n"
        "reichlab/flusion/retrospective-hub,model-output,300\n",
        encoding="utf-8",
    )
    counts = load_hub_row_counts(csv_path)
    key = canon_repo_key("reichlab/flusion/tree/main/retrospective-hub")
    assert counts.get(key) == 300


def test_hub_with_no_stats_returns_none(tmp_path):
    """A hub not present in the summary file should return None."""
    csv_path = tmp_path / "summary.csv"
    csv_path.write_text(
        "repo,dir,row_count\n"
        "org/other-hub,model-output,100\n",
        encoding="utf-8",
    )
    counts = load_hub_row_counts(csv_path)
    assert counts.get("org/missing-hub") is None
