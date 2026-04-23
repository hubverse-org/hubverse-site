import csv
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import polars as pl
import pytest

from scripts.get_hub_stats import (
    count_rows_csv,
    fetch_hub_stats,
    hub_label,
    list_files_in_directory,
    make_session,
    write_summary_csv,
)


# ---------------------------------------------------------------------------
# hub_label
# ---------------------------------------------------------------------------


def test_hub_label_without_subdir():
    assert hub_label("cdcepi", "FluSight-forecast-hub", None) == "cdcepi/FluSight-forecast-hub"


def test_hub_label_with_subdir():
    assert hub_label("reichlab", "flusion", "retrospective-hub") == "reichlab/flusion/retrospective-hub"


def test_hub_label_empty_subdir_treated_as_none():
    assert hub_label("org", "repo", None) == "org/repo"


# ---------------------------------------------------------------------------
# make_session
# ---------------------------------------------------------------------------


def test_make_session_sets_auth_header():
    session = make_session("my-token")
    assert session.headers["Authorization"] == "token my-token"


def test_make_session_sets_accept_header():
    session = make_session("token")
    assert "application/vnd.github" in session.headers["Accept"]


# ---------------------------------------------------------------------------
# count_rows_csv
# ---------------------------------------------------------------------------


def _mock_session_get(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.raise_for_status = MagicMock()
    session = MagicMock()
    session.get.return_value = response
    return session


def test_count_rows_csv_counts_data_rows():
    csv_text = "col1,col2\na,1\nb,2\nc,3\n"
    session = _mock_session_get(csv_text)
    assert count_rows_csv("http://example.com/file.csv", session) == 3


def test_count_rows_csv_header_only_returns_zero():
    session = _mock_session_get("col1,col2\n")
    assert count_rows_csv("http://example.com/file.csv", session) == 0


def test_count_rows_csv_empty_file_returns_zero():
    session = _mock_session_get("")
    assert count_rows_csv("http://example.com/file.csv", session) == 0


# ---------------------------------------------------------------------------
# list_files_in_directory
# ---------------------------------------------------------------------------


def _api_response(items: list[dict], next_url: str | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = items
    response.raise_for_status = MagicMock()
    response.links = {"next": {"url": next_url}} if next_url else {}
    return response


def test_list_files_returns_csv_and_parquet_urls():
    session = MagicMock()
    session.get.return_value = _api_response([
        {"type": "file", "download_url": "https://raw.github.com/org/repo/file.csv"},
        {"type": "file", "download_url": "https://raw.github.com/org/repo/file.parquet"},
        {"type": "file", "download_url": "https://raw.github.com/org/repo/file.txt"},
    ])
    files = list_files_in_directory(session, "org", "repo", "model-output")
    assert len(files) == 2
    assert all(f.endswith((".csv", ".parquet")) for f in files)


def test_list_files_returns_empty_on_404():
    response = MagicMock()
    response.status_code = 404
    session = MagicMock()
    session.get.return_value = response
    files = list_files_in_directory(session, "org", "repo", "target-data")
    assert files == []


def test_list_files_returns_empty_on_403():
    response = MagicMock()
    response.status_code = 403
    session = MagicMock()
    session.get.return_value = response
    files = list_files_in_directory(session, "org", "repo", "model-output")
    assert files == []


# ---------------------------------------------------------------------------
# write_summary_csv
# ---------------------------------------------------------------------------


def _make_parquet(tmp_path: Path, filename: str, rows: list[dict]) -> Path:
    df = pl.DataFrame(rows)
    path = tmp_path / filename
    df.write_parquet(path)
    return path


def test_write_summary_csv_creates_file(tmp_path):
    _make_parquet(tmp_path, "org_repo.parquet", [
        {"repo": "org/repo", "dir": "model-output", "row_count": 100},
        {"repo": "org/repo", "dir": "target-data",  "row_count": 50},
    ])
    summary = tmp_path / "summary.csv"
    write_summary_csv(tmp_path, summary)
    assert summary.exists()


def test_write_summary_csv_sums_per_repo_and_dir(tmp_path):
    _make_parquet(tmp_path, "a.parquet", [
        {"repo": "org/repo", "dir": "model-output", "row_count": 100},
        {"repo": "org/repo", "dir": "model-output", "row_count": 200},
        {"repo": "org/repo", "dir": "target-data",  "row_count": 50},
    ])
    summary = tmp_path / "summary.csv"
    write_summary_csv(tmp_path, summary)
    df = pl.read_csv(summary)
    mo = df.filter((pl.col("repo") == "org/repo") & (pl.col("dir") == "model-output"))
    assert mo["row_count"][0] == 300


def test_write_summary_csv_filters_to_model_output_and_target_data(tmp_path):
    _make_parquet(tmp_path, "a.parquet", [
        {"repo": "org/repo", "dir": "model-output", "row_count": 10},
        {"repo": "org/repo", "dir": "other-dir",    "row_count": 999},
    ])
    summary = tmp_path / "summary.csv"
    write_summary_csv(tmp_path, summary)
    df = pl.read_csv(summary)
    assert "other-dir" not in df["dir"].to_list()


def test_write_summary_csv_handles_multiple_hubs(tmp_path):
    _make_parquet(tmp_path, "hub_a.parquet", [
        {"repo": "org/hub-a", "dir": "model-output", "row_count": 10},
    ])
    _make_parquet(tmp_path, "hub_b.parquet", [
        {"repo": "org/hub-b", "dir": "target-data", "row_count": 20},
    ])
    summary = tmp_path / "summary.csv"
    write_summary_csv(tmp_path, summary)
    df = pl.read_csv(summary)
    assert set(df["repo"].to_list()) == {"org/hub-a", "org/hub-b"}


def test_write_summary_csv_no_parquets_does_not_raise(tmp_path):
    summary = tmp_path / "summary.csv"
    write_summary_csv(tmp_path, summary)
    assert not summary.exists()


# ---------------------------------------------------------------------------
# fetch_hub_stats (integration-style with full mocking)
# ---------------------------------------------------------------------------


def test_fetch_hub_stats_returns_empty_dataframe_when_no_files():
    session = MagicMock()
    response = MagicMock()
    response.status_code = 404
    session.get.return_value = response

    df = fetch_hub_stats(session, "org", "repo", None)
    assert len(df) == 0


def test_fetch_hub_stats_labels_repo_correctly():
    session = MagicMock()
    no_files_response = MagicMock()
    no_files_response.status_code = 404
    session.get.return_value = no_files_response

    df = fetch_hub_stats(session, "reichlab", "flusion", "retrospective-hub")
    assert len(df) == 0  # no files found, but label logic is exercised without error


def test_fetch_hub_stats_concat_succeeds_when_both_dirs_have_files():
    """model-output (5 cols with model_id) and target-data (4 cols) must concat cleanly."""
    csv_url = "https://raw.githubusercontent.com/org/repo/main/model-output/modelA/file.csv"
    csv_url_td = "https://raw.githubusercontent.com/org/repo/main/target-data/file.csv"

    def fake_get(url, **kwargs):
        response = MagicMock()
        response.raise_for_status = MagicMock()
        parsed = urlparse(url)
        # API listing calls
        if parsed.netloc == "api.github.com" and "model-output" in parsed.path:
            response.status_code = 200
            response.json.return_value = [{"type": "file", "download_url": csv_url}]
            response.links = {}
        elif parsed.netloc == "api.github.com" and "target-data" in parsed.path:
            response.status_code = 200
            response.json.return_value = [{"type": "file", "download_url": csv_url_td}]
            response.links = {}
        # CSV download calls
        else:
            response.status_code = 200
            response.text = "col\nval\n"
        return response

    session = MagicMock()
    session.get.side_effect = fake_get

    # Should not raise ShapeError
    df = fetch_hub_stats(session, "org", "repo", None)
    assert "model_id" in df.columns
    assert "dir" in df.columns
