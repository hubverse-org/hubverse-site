import csv
import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlparse

import polars as pl
import pytest

import scripts.get_hub_stats as mod
from scripts.get_hub_stats import (
    _count_files,
    _is_data_file,
    count_rows,
    count_rows_csv,
    count_rows_parquet,
    fetch_hub_stats,
    fetch_full_tree,
    fetch_subtree_recursive,
    get_repo_info,
    get_tree_sha,
    hub_label,
    list_files_for_archived_pattern,
    list_files_for_directory,
    load_fetch_cache,
    make_session,
    parse_archived_dir,
    process_hub,
    save_fetch_cache,
    write_fetch_errors_report,
    write_summary_csv,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api_response(body, status=200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.raise_for_status = MagicMock()
    if isinstance(body, dict):
        r.json.return_value = body
    elif isinstance(body, list):
        r.json.return_value = body
    else:
        r.text = body
    return r


def _raw_url(owner, repo, branch, path):
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"


# ---------------------------------------------------------------------------
# hub_label
# ---------------------------------------------------------------------------


def test_hub_label_without_subdir():
    assert hub_label("cdcepi", "FluSight-forecast-hub", None) == "cdcepi/FluSight-forecast-hub"


def test_hub_label_with_subdir():
    assert hub_label("reichlab", "flusion", "retrospective-hub") == "reichlab/flusion/retrospective-hub"


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


def _mock_session(text: str) -> MagicMock:
    session = MagicMock()
    session.get.return_value = _api_response(text)
    return session


def test_count_rows_csv_counts_data_rows():
    assert count_rows_csv("http://x/f.csv", _mock_session("col\na\nb\nc\n")) == 3


def test_count_rows_csv_header_only_returns_zero():
    assert count_rows_csv("http://x/f.csv", _mock_session("col\n")) == 0


def test_count_rows_csv_empty_file_returns_zero():
    assert count_rows_csv("http://x/f.csv", _mock_session("")) == 0


# ---------------------------------------------------------------------------
# count_rows_parquet / count_rows
# ---------------------------------------------------------------------------


def test_count_rows_parquet_reads_row_count_from_metadata(tmp_path):
    # Runs the real DuckDB query against a local file. This is the regression
    # test for DuckDB 2.0 removing fetchone() from relations, which silently
    # zeroed every parquet file's count.
    path = tmp_path / "f.parquet"
    pl.DataFrame({"x": list(range(7))}).write_parquet(path)
    assert count_rows_parquet(str(path)) == 7


def test_count_rows_parquet_empty_file_returns_zero(tmp_path):
    path = tmp_path / "empty.parquet"
    pl.DataFrame({"x": pl.Series([], dtype=pl.Int64)}).write_parquet(path)
    assert count_rows_parquet(str(path)) == 0


def test_count_rows_success_returns_no_error():
    url = "https://raw.githubusercontent.com/org/repo/main/model-output/m/f.csv"
    assert count_rows(url, _mock_session("col\na\nb\n")) == (url, 2, None)


def test_count_rows_failure_returns_error_message(monkeypatch):
    def boom(file_url):
        raise RuntimeError("parquet exploded")
    monkeypatch.setattr(mod, "count_rows_parquet", boom)
    url = "https://raw.githubusercontent.com/org/repo/main/model-output/m/f.parquet"
    assert count_rows(url, MagicMock()) == (url, 0, "parquet exploded")


def test_count_rows_failure_is_logged(monkeypatch, capsys):
    def boom(file_url):
        raise ValueError("bad")
    monkeypatch.setattr(mod, "count_rows_parquet", boom)
    count_rows("https://x/f.parquet", MagicMock())
    assert "Error processing https://x/f.parquet: bad" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _is_data_file
# ---------------------------------------------------------------------------


def test_is_data_file_csv():
    assert _is_data_file("model-output/modelA/file.csv")


def test_is_data_file_parquet():
    assert _is_data_file("model-output/modelA/file.parquet")


def test_is_data_file_uppercase():
    assert _is_data_file("model-output/modelA/FILE.CSV")


def test_is_data_file_rejects_other():
    assert not _is_data_file("README.md")
    assert not _is_data_file("model-output/modelA/file.txt")


# ---------------------------------------------------------------------------
# get_repo_info
# ---------------------------------------------------------------------------


def test_get_repo_info_returns_pushed_at_and_default_branch():
    session = MagicMock()
    session.get.return_value = _api_response({
        "pushed_at": "2026-06-15T12:00:00Z",
        "default_branch": "main",
    })
    pushed_at, branch = get_repo_info(session, "org", "repo")
    assert pushed_at == "2026-06-15T12:00:00Z"
    assert branch == "main"


# ---------------------------------------------------------------------------
# get_tree_sha
# ---------------------------------------------------------------------------


def test_get_tree_sha_extracts_sha():
    session = MagicMock()
    session.get.return_value = _api_response({
        "commit": {"commit": {"tree": {"sha": "abc123"}}}
    })
    assert get_tree_sha(session, "org", "repo", "main") == "abc123"


# ---------------------------------------------------------------------------
# fetch_subtree_recursive
# ---------------------------------------------------------------------------


def test_fetch_subtree_recursive_returns_blobs():
    session = MagicMock()
    session.get.return_value = _api_response({
        "tree": [
            {"type": "blob", "path": "file.csv", "sha": "aaa"},
            {"type": "blob", "path": "file.parquet", "sha": "bbb"},
        ]
    })
    entries = fetch_subtree_recursive(session, "org", "repo", "sha123")
    assert len(entries) == 2
    assert all(e["type"] == "blob" for e in entries)


def test_fetch_subtree_recursive_prepends_prefix():
    session = MagicMock()
    session.get.return_value = _api_response({
        "tree": [{"type": "blob", "path": "file.csv", "sha": "aaa"}]
    })
    entries = fetch_subtree_recursive(session, "org", "repo", "sha", "model-output/modelA")
    assert entries[0]["path"] == "model-output/modelA/file.csv"


def test_fetch_subtree_recursive_recurses_into_subtrees():
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if "sha_root" in url:
            return _api_response({
                "tree": [
                    {"type": "tree", "path": "subdir", "sha": "sha_sub"},
                    {"type": "blob", "path": "root_file.csv", "sha": "r"},
                ]
            })
        else:  # sha_sub
            return _api_response({
                "tree": [{"type": "blob", "path": "nested.csv", "sha": "n"}]
            })

    session = MagicMock()
    session.get.side_effect = fake_get

    entries = fetch_subtree_recursive(session, "org", "repo", "sha_root")
    paths = {e["path"] for e in entries}
    assert "root_file.csv" in paths
    assert "subdir/nested.csv" in paths


# ---------------------------------------------------------------------------
# fetch_full_tree
# ---------------------------------------------------------------------------


def test_fetch_full_tree_returns_blobs_when_not_truncated():
    session = MagicMock()
    session.get.return_value = _api_response({
        "truncated": False,
        "tree": [
            {"type": "blob", "path": "model-output/modelA/file.csv"},
            {"type": "tree", "path": "model-output/modelA"},
        ],
    })
    entries = fetch_full_tree(session, "org", "repo", "sha")
    assert len(entries) == 1
    assert entries[0]["path"] == "model-output/modelA/file.csv"


def test_fetch_full_tree_falls_back_on_truncation(monkeypatch):
    """When truncated=True, fetch_full_tree should use fetch_subtree_recursive."""
    import scripts.get_hub_stats as mod

    recursive_called = []

    def fake_subtree(session, owner, repo, tree_sha, path_prefix=""):
        recursive_called.append(True)
        return [{"type": "blob", "path": "model-output/modelA/file.csv"}]

    monkeypatch.setattr(mod, "fetch_subtree_recursive", fake_subtree)

    session = MagicMock()
    session.get.return_value = _api_response({
        "truncated": True,
        "tree": [{"type": "blob", "path": "partial.csv"}],
    })

    entries = fetch_full_tree(session, "org", "repo", "sha")
    assert recursive_called, "fetch_subtree_recursive should have been called"
    assert entries[0]["path"] == "model-output/modelA/file.csv"


# ---------------------------------------------------------------------------
# list_files_for_directory
# ---------------------------------------------------------------------------

TREE = [
    {"type": "blob", "path": "model-output/modelA/file1.csv"},
    {"type": "blob", "path": "model-output/modelA/file2.parquet"},
    {"type": "blob", "path": "model-output/modelA/notes.txt"},
    {"type": "blob", "path": "target-data/obs.csv"},
    {"type": "blob", "path": "README.md"},
]


def test_list_files_for_directory_returns_csv_and_parquet():
    pairs = list_files_for_directory(TREE, "model-output", "org", "repo", "main")
    assert len(pairs) == 2
    urls = [url for url, _ in pairs]
    assert all("model-output" in u for u in urls)
    assert not any("notes.txt" in u for u in urls)


def test_list_files_for_directory_source_dir_equals_directory():
    pairs = list_files_for_directory(TREE, "target-data", "org", "repo", "main")
    assert all(src == "target-data" for _, src in pairs)


def test_list_files_for_directory_constructs_raw_urls():
    pairs = list_files_for_directory(TREE, "model-output", "org", "repo", "main")
    assert all(u.startswith("https://raw.githubusercontent.com/org/repo/main/") for u, _ in pairs)


def test_list_files_for_directory_empty_when_no_match():
    pairs = list_files_for_directory(TREE, "nonexistent", "org", "repo", "main")
    assert pairs == []


def test_list_files_for_directory_with_subdir_prefix():
    tree = [
        {"type": "blob", "path": "subhub/model-output/modelA/file.csv"},
        {"type": "blob", "path": "model-output/modelA/file.csv"},  # not under subhub/
    ]
    pairs = list_files_for_directory(tree, "subhub/model-output", "org", "repo", "main")
    assert len(pairs) == 1
    assert "subhub/model-output" in pairs[0][0]


# ---------------------------------------------------------------------------
# list_files_for_archived_pattern
# ---------------------------------------------------------------------------

ARCHIVED_TREE = [
    {"type": "blob", "path": "Previous_Rounds/round_1/model-output/modelA/f1.csv"},
    {"type": "blob", "path": "Previous_Rounds/round_2/model-output/modelA/f2.parquet"},
    {"type": "blob", "path": "Previous_Rounds/round_1/model-output/modelA/notes.txt"},
    {"type": "blob", "path": "model-output/modelA/current.csv"},
    {"type": "blob", "path": "Previous_Rounds/round_1/target-data/obs.csv"},
]


def test_list_files_for_archived_pattern_matches_wildcard():
    pairs = list_files_for_archived_pattern(
        ARCHIVED_TREE, "Previous_Rounds/*/model-output", "org", "repo", "main"
    )
    assert len(pairs) == 2  # f1.csv and f2.parquet (not notes.txt, not current.csv, not obs.csv)


def test_list_files_for_archived_pattern_source_dir_is_expanded():
    pairs = list_files_for_archived_pattern(
        ARCHIVED_TREE, "Previous_Rounds/*/model-output", "org", "repo", "main"
    )
    source_dirs = {src for _, src in pairs}
    assert "Previous_Rounds/round_1/model-output" in source_dirs
    assert "Previous_Rounds/round_2/model-output" in source_dirs


def test_list_files_for_archived_pattern_different_bucket():
    pairs = list_files_for_archived_pattern(
        ARCHIVED_TREE, "Previous_Rounds/*/target-data", "org", "repo", "main"
    )
    assert len(pairs) == 1
    assert "target-data" in pairs[0][1]


def test_list_files_for_archived_pattern_no_match():
    pairs = list_files_for_archived_pattern(
        ARCHIVED_TREE, "Old/*/model-output", "org", "repo", "main"
    )
    assert pairs == []


def test_list_files_for_archived_pattern_literal_pattern_no_wildcard():
    """A pattern with no wildcard acts as a literal path prefix."""
    tree = [{"type": "blob", "path": "archive/model-output/modelA/file.csv"}]
    pairs = list_files_for_archived_pattern(
        tree, "archive/model-output", "org", "repo", "main"
    )
    assert len(pairs) == 1
    assert pairs[0][1] == "archive/model-output"


# ---------------------------------------------------------------------------
# parse_archived_dir
# ---------------------------------------------------------------------------

def test_parse_archived_dir_string_takes_bucket_from_last_segment():
    assert parse_archived_dir("Previous_Rounds/*/model-output") == (
        "Previous_Rounds/*/model-output", "model-output",
    )
    assert parse_archived_dir("Previous_Rounds/*/target-data/") == (
        "Previous_Rounds/*/target-data/", "target-data",
    )


def test_parse_archived_dir_mapping_uses_explicit_bucket():
    entry = {"path": "auxiliary-data/target-data-archive/*", "bucket": "target-data"}
    assert parse_archived_dir(entry) == (
        "auxiliary-data/target-data-archive/*", "target-data",
    )


def test_parse_archived_dir_unknown_bucket_returns_none(capsys):
    assert parse_archived_dir("Previous_Rounds/*/raw") is None
    assert parse_archived_dir({"path": "archive/*", "bucket": "raw"}) is None
    assert capsys.readouterr().out.count("unrecognised bucket") == 2


@pytest.mark.parametrize("entry", [
    {"path": "archive/*"},                         # missing bucket
    {"bucket": "target-data"},                     # missing path
    {"path": ["archive/*"], "bucket": "target-data"},
    ["archive/*", "target-data"],
    42,
])
def test_parse_archived_dir_malformed_returns_none(entry, capsys):
    assert parse_archived_dir(entry) is None
    assert "malformed archived_dirs entry" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _count_files
# ---------------------------------------------------------------------------


def test_count_files_returns_dataframe_with_correct_columns():
    session = MagicMock()
    session.get.return_value = _api_response("col\nval\n")
    df, _ = _count_files(
        ["https://raw.githubusercontent.com/org/repo/main/model-output/modelA/f.csv"],
        session, "org/repo", "model-output", "model-output",
    )
    assert set(df.columns) >= {"file", "row_count", "dir", "source_dir", "repo", "model_id"}


def test_count_files_source_dir_distinct_from_dir_for_archived():
    session = MagicMock()
    session.get.return_value = _api_response("col\nval\n")
    archived = "Previous_Rounds/round_1/model-output"
    df, _ = _count_files(
        [f"https://raw.githubusercontent.com/org/repo/main/{archived}/modelA/f.csv"],
        session, "org/repo", "model-output", archived,
    )
    assert df["source_dir"][0] == archived
    assert df["dir"][0] == "model-output"


def test_count_files_model_id_null_for_target_data():
    session = MagicMock()
    session.get.return_value = _api_response("col\nval\n")
    df, _ = _count_files(
        ["https://raw.githubusercontent.com/org/repo/main/target-data/obs.csv"],
        session, "org/repo", "target-data", "target-data",
    )
    assert df["model_id"][0] is None


def test_count_files_reports_no_failures_on_success():
    session = _mock_session("col\nval\n")
    _, failures = _count_files(
        ["https://raw.githubusercontent.com/org/repo/main/target-data/obs.csv"],
        session, "org/repo", "target-data", "target-data",
    )
    assert failures == []


def test_count_files_reports_failed_file_with_message():
    good = "https://raw.githubusercontent.com/org/repo/main/model-output/m/good.csv"
    bad = "https://raw.githubusercontent.com/org/repo/main/model-output/m/bad.csv"

    def fake_get(url, **kwargs):
        if url == bad:
            raise ConnectionError("download failed")
        return _api_response("col\nval\n")
    session = MagicMock()
    session.get.side_effect = fake_get

    df, failures = _count_files([good, bad], session, "org/repo", "model-output", "model-output")
    assert failures == [(bad, "download failed")]
    # the good file is still counted
    assert df.filter(pl.col("file") == good)["row_count"][0] == 1


# ---------------------------------------------------------------------------
# write_summary_csv
# ---------------------------------------------------------------------------


def _make_parquet(tmp_path: Path, filename: str, rows: list[dict]) -> Path:
    path = tmp_path / filename
    pl.DataFrame(rows).write_parquet(path)
    return path


def test_write_summary_csv_creates_file(tmp_path):
    _make_parquet(tmp_path, "hub.parquet", [
        {"repo": "org/hub", "dir": "model-output", "row_count": 100},
    ])
    summary = tmp_path / "summary.csv"
    write_summary_csv(tmp_path, summary)
    assert summary.exists()


def test_write_summary_csv_sums_per_repo_and_dir(tmp_path):
    _make_parquet(tmp_path, "a.parquet", [
        {"repo": "org/hub", "dir": "model-output", "row_count": 100},
        {"repo": "org/hub", "dir": "model-output", "row_count": 200},
    ])
    write_summary_csv(tmp_path, tmp_path / "s.csv")
    df = pl.read_csv(tmp_path / "s.csv")
    assert df.filter(pl.col("dir") == "model-output")["row_count"][0] == 300


def test_write_summary_csv_filters_to_canonical_dirs(tmp_path):
    _make_parquet(tmp_path, "a.parquet", [
        {"repo": "org/hub", "dir": "model-output", "row_count": 10},
        {"repo": "org/hub", "dir": "Previous_Rounds/round_1/model-output", "row_count": 999},
    ])
    write_summary_csv(tmp_path, tmp_path / "s.csv")
    df = pl.read_csv(tmp_path / "s.csv")
    assert "Previous_Rounds/round_1/model-output" not in df["dir"].to_list()


def test_write_summary_csv_no_parquets_does_not_raise(tmp_path):
    summary = tmp_path / "summary.csv"
    write_summary_csv(tmp_path, summary)
    assert not summary.exists()


# ---------------------------------------------------------------------------
# fetch_hub_stats
# ---------------------------------------------------------------------------


def _make_session_for_tree(tree_entries, csv_rows=1):
    """Session that serves tree API and CSV downloads."""
    def fake_get(url, **kwargs):
        parsed = urlparse(url)
        if parsed.netloc == "api.github.com":
            return _api_response({"truncated": False, "tree": tree_entries})
        # CSV download
        return _api_response("col\n" + "\n".join(["val"] * csv_rows) + "\n")
    session = MagicMock()
    session.get.side_effect = fake_get
    return session


def test_fetch_hub_stats_empty_when_no_files():
    session = MagicMock()
    df, _ = fetch_hub_stats(session, "org", "repo", None, None, "main", [])
    assert len(df) == 0


def test_fetch_hub_stats_counts_model_output_files():
    tree = [{"type": "blob", "path": "model-output/modelA/file.csv"}]
    session = _make_session_for_tree(tree, csv_rows=3)
    df, _ = fetch_hub_stats(session, "org", "repo", None, None, "main", tree)
    assert df["row_count"].sum() == 3


def test_fetch_hub_stats_includes_source_dir_column():
    tree = [{"type": "blob", "path": "model-output/modelA/file.csv"}]
    session = _make_session_for_tree(tree)
    df, _ = fetch_hub_stats(session, "org", "repo", None, None, "main", tree)
    assert "source_dir" in df.columns


def test_fetch_hub_stats_archived_dirs_counted():
    tree = [
        {"type": "blob", "path": "model-output/modelA/current.csv"},
        {"type": "blob", "path": "Previous_Rounds/round_1/model-output/modelA/old.csv"},
    ]
    session = _make_session_for_tree(tree, csv_rows=2)
    df, _ = fetch_hub_stats(
        session, "org", "repo", None,
        ["Previous_Rounds/*/model-output"], "main", tree,
    )
    source_dirs = df["source_dir"].to_list()
    assert "model-output" in source_dirs
    assert "Previous_Rounds/round_1/model-output" in source_dirs


def test_fetch_hub_stats_archived_unknown_bucket_skipped(capsys):
    tree = [{"type": "blob", "path": "weird/round_1/outputs/file.csv"}]
    session = _make_session_for_tree(tree)
    fetch_hub_stats(session, "org", "repo", None, ["weird/*/outputs"], "main", tree)
    assert "unrecognised bucket" in capsys.readouterr().out


def test_fetch_hub_stats_with_hub_subdir():
    tree = [{"type": "blob", "path": "retrospective-hub/model-output/modelA/file.csv"}]
    session = _make_session_for_tree(tree, csv_rows=5)
    df, _ = fetch_hub_stats(session, "reichlab", "flusion", "retrospective-hub", None, "main", tree)
    assert df["repo"][0] == "reichlab/flusion/retrospective-hub"
    assert df["row_count"].sum() == 5


def test_fetch_hub_stats_counts_mapping_archive_under_explicit_bucket():
    # The ai4casting layout: last season moved to a folder whose name isn't
    # a bucket, so the bucket must be given explicitly.
    tree = [
        {"type": "blob", "path": "target-data/season_2026_2027/data.csv"},
        {"type": "blob", "path": "auxiliary-data/target-data-archive/season_2024_2025/data.csv"},
        {"type": "blob", "path": "auxiliary-data/target-data-archive/season_2025_2026/data.csv"},
        {"type": "blob", "path": "auxiliary-data/season_2025_2026_raw_files/raw.csv"},  # not archived
    ]
    archive = [{"path": "auxiliary-data/target-data-archive/*", "bucket": "target-data"}]
    df, failures = fetch_hub_stats(
        _make_session_for_tree(tree, csv_rows=2), "org", "repo", None, archive, "main", tree,
    )
    assert failures == []
    assert set(df["dir"].to_list()) == {"target-data"}
    assert sorted(df["source_dir"].to_list()) == [
        "auxiliary-data/target-data-archive/season_2024_2025",
        "auxiliary-data/target-data-archive/season_2025_2026",
        "target-data",
    ]
    assert not any("raw_files" in f for f in df["file"].to_list())
    assert df["row_count"].sum() == 6  # 3 files x 2 rows


def test_fetch_hub_stats_mixes_string_and_mapping_entries():
    tree = [
        {"type": "blob", "path": "Previous_Rounds/r1/model-output/modelA/a.csv"},
        {"type": "blob", "path": "archive/old/obs.csv"},
    ]
    archived = [
        "Previous_Rounds/*/model-output",
        {"path": "archive/*", "bucket": "target-data"},
    ]
    df, _ = fetch_hub_stats(_make_session_for_tree(tree), "org", "repo", None, archived, "main", tree)
    by_source = dict(zip(df["source_dir"].to_list(), df["dir"].to_list()))
    assert by_source == {
        "Previous_Rounds/r1/model-output": "model-output",
        "archive/old": "target-data",
    }


def test_fetch_hub_stats_skips_malformed_mapping_without_crashing(capsys):
    tree = [{"type": "blob", "path": "archive/old/obs.csv"}]
    df, failures = fetch_hub_stats(
        _make_session_for_tree(tree), "org", "repo", None, [{"path": "archive/*"}], "main", tree,
    )
    assert len(df) == 0 and failures == []
    assert "malformed archived_dirs entry" in capsys.readouterr().out


def test_fetch_hub_stats_returns_no_failures_on_success():
    tree = [{"type": "blob", "path": "model-output/modelA/file.csv"}]
    _, failures = fetch_hub_stats(_make_session_for_tree(tree), "org", "repo", None, None, "main", tree)
    assert failures == []


def test_fetch_hub_stats_collects_failures_across_dirs(monkeypatch):
    def boom(file_url):
        raise RuntimeError("no fetchone")
    monkeypatch.setattr(mod, "count_rows_parquet", boom)
    tree = [
        {"type": "blob", "path": "model-output/modelA/a.parquet"},
        {"type": "blob", "path": "target-data/oracle-output.parquet"},
        {"type": "blob", "path": "target-data/time-series.csv"},
    ]
    _, failures = fetch_hub_stats(_make_session_for_tree(tree), "org", "repo", None, None, "main", tree)
    failed_files = sorted(url.rsplit("/", 1)[-1] for url, _ in failures)
    assert failed_files == ["a.parquet", "oracle-output.parquet"]
    assert all(message == "no fetchone" for _, message in failures)


# ---------------------------------------------------------------------------
# load_fetch_cache / save_fetch_cache
# ---------------------------------------------------------------------------


def test_save_and_load_fetch_cache_round_trips(tmp_path):
    cache = {"org/hub": "2026-06-15T12:00:00Z", "org/hub2": "2026-06-01T00:00:00Z"}
    path = tmp_path / "fetch_cache.json"
    save_fetch_cache(cache, path)
    loaded = load_fetch_cache(path)
    assert loaded == cache


def test_load_fetch_cache_returns_empty_dict_when_missing(tmp_path):
    result = load_fetch_cache(tmp_path / "nonexistent.json")
    assert result == {}


def test_save_fetch_cache_is_sorted(tmp_path):
    path = tmp_path / "cache.json"
    save_fetch_cache({"b/repo": "ts2", "a/repo": "ts1"}, path)
    data = json.loads(path.read_text())
    assert list(data.keys()) == ["a/repo", "b/repo"]


# ---------------------------------------------------------------------------
# process_hub – skip logic
# ---------------------------------------------------------------------------


def _make_process_hub_session(pushed_at="2026-06-15T12:00:00Z", default_branch="main"):
    """Session that satisfies get_repo_info, get_tree_sha, fetch_full_tree, and CSV downloads."""
    def fake_get(url, **kwargs):
        parsed = urlparse(url)
        if "/repos/org/repo" in url and "/branches/" not in url and "/git/" not in url:
            return _api_response({"pushed_at": pushed_at, "default_branch": default_branch})
        if "/branches/" in url:
            return _api_response({"commit": {"commit": {"tree": {"sha": "treeSHA"}}}})
        if "/git/trees/" in url:
            return _api_response({"truncated": False, "tree": [
                {"type": "blob", "path": "model-output/modelA/file.csv"}
            ]})
        # CSV download
        return _api_response("col\nval\n")
    session = MagicMock()
    session.get.side_effect = fake_get
    return session


def test_process_hub_skips_when_pushed_at_unchanged(tmp_path):
    label = "org/repo"
    parquet = tmp_path / "org_repo.parquet"
    pl.DataFrame({"repo": ["org/repo"], "dir": ["model-output"], "row_count": [100]}).write_parquet(parquet)

    cache = {label: "2026-06-15T12:00:00Z"}
    session = _make_process_hub_session(pushed_at="2026-06-15T12:00:00Z")

    process_hub(session, "org", "repo", None, tmp_path, fetch_cache=cache)
    # Session should only have been called once (get_repo_info), not for tree/files
    api_calls = [str(c.args[0]) for c in session.get.call_args_list]
    assert not any("/git/trees/" in u for u in api_calls)


def test_process_hub_fetches_when_pushed_at_changed(tmp_path):
    label = "org/repo"
    parquet = tmp_path / "org_repo.parquet"
    pl.DataFrame({"repo": ["org/repo"], "dir": ["model-output"], "row_count": [100]}).write_parquet(parquet)

    cache = {label: "2026-06-01T00:00:00Z"}  # stale
    session = _make_process_hub_session(pushed_at="2026-06-15T12:00:00Z")

    process_hub(session, "org", "repo", None, tmp_path, fetch_cache=cache)
    api_calls = [str(c.args[0]) for c in session.get.call_args_list]
    assert any("/git/trees/" in u for u in api_calls)


def test_process_hub_updates_cache_after_fetch(tmp_path):
    cache = {}
    session = _make_process_hub_session(pushed_at="2026-06-15T12:00:00Z")
    process_hub(session, "org", "repo", None, tmp_path, fetch_cache=cache)
    assert cache.get("org/repo") == "2026-06-15T12:00:00Z"


def test_process_hub_force_refetches_even_if_cache_matches(tmp_path):
    label = "org/repo"
    parquet = tmp_path / "org_repo.parquet"
    pl.DataFrame({"repo": ["org/repo"], "dir": ["model-output"], "row_count": [100]}).write_parquet(parquet)

    pushed_at = "2026-06-15T12:00:00Z"
    cache = {label: pushed_at}
    session = _make_process_hub_session(pushed_at=pushed_at)

    process_hub(session, "org", "repo", None, tmp_path, fetch_cache=cache, force=True)
    api_calls = [str(c.args[0]) for c in session.get.call_args_list]
    assert any("/git/trees/" in u for u in api_calls)


# ---------------------------------------------------------------------------
# process_hub – failure handling (never overwrite good data with zeros)
# ---------------------------------------------------------------------------


def _fail_csv_counts(monkeypatch, message="boom"):
    def boom(file_url, session):
        raise RuntimeError(message)
    monkeypatch.setattr(mod, "count_rows_csv", boom)


def _write_previous(tmp_path, row_count=100) -> Path:
    parquet = tmp_path / "org_repo.parquet"
    pl.DataFrame({"repo": ["org/repo"], "dir": ["model-output"], "row_count": [row_count]}).write_parquet(parquet)
    return parquet


def test_process_hub_returns_empty_list_on_success(tmp_path):
    session = _make_process_hub_session()
    assert process_hub(session, "org", "repo", None, tmp_path, fetch_cache={}) == []


def test_process_hub_returns_empty_list_when_skipped(tmp_path):
    _write_previous(tmp_path)
    pushed_at = "2026-06-15T12:00:00Z"
    session = _make_process_hub_session(pushed_at=pushed_at)
    assert process_hub(session, "org", "repo", None, tmp_path, fetch_cache={"org/repo": pushed_at}) == []


def test_process_hub_keeps_previous_parquet_on_failure(tmp_path, monkeypatch):
    parquet = _write_previous(tmp_path, row_count=100)
    _fail_csv_counts(monkeypatch)
    session = _make_process_hub_session(pushed_at="2026-06-15T12:00:00Z")

    process_hub(session, "org", "repo", None, tmp_path, fetch_cache={"org/repo": "old"})
    assert pl.read_parquet(parquet)["row_count"].sum() == 100


def test_process_hub_does_not_update_cache_on_failure(tmp_path, monkeypatch):
    _write_previous(tmp_path)
    _fail_csv_counts(monkeypatch)
    cache = {"org/repo": "2026-06-01T00:00:00Z"}
    session = _make_process_hub_session(pushed_at="2026-06-15T12:00:00Z")

    process_hub(session, "org", "repo", None, tmp_path, fetch_cache=cache)
    assert cache["org/repo"] == "2026-06-01T00:00:00Z"


def test_process_hub_returns_failures_with_messages(tmp_path, monkeypatch):
    _fail_csv_counts(monkeypatch, message="rate limited")
    session = _make_process_hub_session()

    failures = process_hub(session, "org", "repo", None, tmp_path, fetch_cache={})
    assert len(failures) == 1
    url, message = failures[0]
    assert url.endswith("model-output/modelA/file.csv")
    assert message == "rate limited"


def test_process_hub_writes_nothing_on_failure_without_previous_stats(tmp_path, monkeypatch):
    _fail_csv_counts(monkeypatch)
    cache = {}
    session = _make_process_hub_session()

    process_hub(session, "org", "repo", None, tmp_path, fetch_cache=cache)
    assert not (tmp_path / "org_repo.parquet").exists()
    assert "org/repo" not in cache


def test_process_hub_retries_on_next_run_after_failure(tmp_path, monkeypatch):
    # A failed run leaves the cache stale, so the next (healthy) run re-fetches
    # the hub instead of skipping it.
    pushed_at = "2026-06-15T12:00:00Z"
    _write_previous(tmp_path)
    cache = {"org/repo": "2026-06-01T00:00:00Z"}

    _fail_csv_counts(monkeypatch)
    process_hub(_make_process_hub_session(pushed_at=pushed_at), "org", "repo", None, tmp_path, fetch_cache=cache)
    monkeypatch.undo()

    session = _make_process_hub_session(pushed_at=pushed_at)
    assert process_hub(session, "org", "repo", None, tmp_path, fetch_cache=cache) == []
    assert any("/git/trees/" in str(c.args[0]) for c in session.get.call_args_list)
    assert cache["org/repo"] == pushed_at


# ---------------------------------------------------------------------------
# write_fetch_errors_report
# ---------------------------------------------------------------------------


def test_write_fetch_errors_report_lists_hub_count_and_error(tmp_path):
    report = tmp_path / "errors.md"
    errors = {"reichlab/variant-nowcast-hub": [(f"https://x/{i}.parquet", "no fetchone") for i in range(2354)]}
    write_fetch_errors_report(errors, report)
    text = report.read_text()
    assert "Files that could not be counted" in text
    assert "| `reichlab/variant-nowcast-hub` | 2,354 | no fetchone |" in text


def test_write_fetch_errors_report_sorts_hubs_case_insensitively(tmp_path):
    report = tmp_path / "errors.md"
    errors = {"reichlab/b": [("u", "e")], "CDCgov/a": [("u", "e")], "midas/c": [("u", "e")]}
    write_fetch_errors_report(errors, report)
    rows = [line for line in report.read_text().splitlines() if line.startswith("| `")]
    assert [r.split("`")[1] for r in rows] == ["CDCgov/a", "midas/c", "reichlab/b"]


def test_write_fetch_errors_report_notes_other_error_types(tmp_path):
    report = tmp_path / "errors.md"
    errors = {"org/repo": [("u1", "common"), ("u2", "common"), ("u3", "rare")]}
    write_fetch_errors_report(errors, report)
    assert "common (+1 other error type(s))" in report.read_text()


def test_write_fetch_errors_report_makes_message_table_safe(tmp_path):
    report = tmp_path / "errors.md"
    errors = {"org/repo": [("u", "bad | pipe\nand newline " + "x" * 300)]}
    write_fetch_errors_report(errors, report)
    row = next(line for line in report.read_text().splitlines() if line.startswith("| `org/repo`"))
    assert "bad \\| pipe and newline" in row
    assert "\n" not in row
    assert "…" in row  # long messages are truncated


def test_write_fetch_errors_report_removes_stale_report_when_no_errors(tmp_path):
    report = tmp_path / "errors.md"
    report.write_text("old report")
    write_fetch_errors_report({}, report)
    assert not report.exists()


def test_write_fetch_errors_report_writes_nothing_when_no_errors(tmp_path):
    report = tmp_path / "errors.md"
    write_fetch_errors_report({}, report)
    assert not report.exists()
