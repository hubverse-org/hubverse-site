import csv
import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlparse

import polars as pl
import pytest

from scripts.get_hub_stats import (
    _count_files,
    _is_data_file,
    count_rows_csv,
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
    process_hub,
    save_fetch_cache,
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
# _count_files
# ---------------------------------------------------------------------------


def test_count_files_returns_dataframe_with_correct_columns():
    session = MagicMock()
    session.get.return_value = _api_response("col\nval\n")
    df = _count_files(
        ["https://raw.githubusercontent.com/org/repo/main/model-output/modelA/f.csv"],
        session, "org/repo", "model-output", "model-output",
    )
    assert set(df.columns) >= {"file", "row_count", "dir", "source_dir", "repo", "model_id"}


def test_count_files_source_dir_distinct_from_dir_for_archived():
    session = MagicMock()
    session.get.return_value = _api_response("col\nval\n")
    archived = "Previous_Rounds/round_1/model-output"
    df = _count_files(
        [f"https://raw.githubusercontent.com/org/repo/main/{archived}/modelA/f.csv"],
        session, "org/repo", "model-output", archived,
    )
    assert df["source_dir"][0] == archived
    assert df["dir"][0] == "model-output"


def test_count_files_model_id_null_for_target_data():
    session = MagicMock()
    session.get.return_value = _api_response("col\nval\n")
    df = _count_files(
        ["https://raw.githubusercontent.com/org/repo/main/target-data/obs.csv"],
        session, "org/repo", "target-data", "target-data",
    )
    assert df["model_id"][0] is None


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
    df = fetch_hub_stats(session, "org", "repo", None, None, "main", [])
    assert len(df) == 0


def test_fetch_hub_stats_counts_model_output_files():
    tree = [{"type": "blob", "path": "model-output/modelA/file.csv"}]
    session = _make_session_for_tree(tree, csv_rows=3)
    df = fetch_hub_stats(session, "org", "repo", None, None, "main", tree)
    assert df["row_count"].sum() == 3


def test_fetch_hub_stats_includes_source_dir_column():
    tree = [{"type": "blob", "path": "model-output/modelA/file.csv"}]
    session = _make_session_for_tree(tree)
    df = fetch_hub_stats(session, "org", "repo", None, None, "main", tree)
    assert "source_dir" in df.columns


def test_fetch_hub_stats_archived_dirs_counted():
    tree = [
        {"type": "blob", "path": "model-output/modelA/current.csv"},
        {"type": "blob", "path": "Previous_Rounds/round_1/model-output/modelA/old.csv"},
    ]
    session = _make_session_for_tree(tree, csv_rows=2)
    df = fetch_hub_stats(
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
    df = fetch_hub_stats(session, "reichlab", "flusion", "retrospective-hub", None, "main", tree)
    assert df["repo"][0] == "reichlab/flusion/retrospective-hub"
    assert df["row_count"].sum() == 5


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
