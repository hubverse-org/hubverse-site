"""Get row counts for hub model-output and target-data files.

Reads output/hubs.json, counts rows in each hub's model-output and
target-data directories via the GitHub API, and writes a summary CSV
to output/hub_stats_summary.csv.

Per-hub results are cached as parquet files in output/hub_stats/ and
committed to the repo alongside hub_stats_summary.csv.  A companion
fetch_cache.json (also committed) records the GitHub pushed_at timestamp
seen at the time of each hub's last fetch.  On subsequent runs, hubs
whose pushed_at has not changed are skipped entirely, so only hubs with
new data incur API calls.

File listing uses the Git Trees API (one call per repo) instead of the
recursive Contents API (which fails with 403 for large directories and
requires many sequential calls).  For repos whose tree response is
truncated (>100 k entries), the script falls back to per-subtree calls.

Notes
-----
Requires a GITHUB_TOKEN environment variable with read access to
public repositories.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "polars",
#   "requests",
# ]
# ///

import argparse
import concurrent.futures
import csv
import datetime
import json
import os
from collections import defaultdict
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

import duckdb
import polars as pl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set > 0 to cap files per directory (useful for local testing).
FILE_COUNT = 0

# Maximum concurrent file-download threads per hub directory.
MAX_WORKERS = 10


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


def make_session(token: str) -> requests.Session:
    """Return a requests Session with auth headers and automatic retry.

    Retries on rate-limit (429) and transient server errors (5xx) with
    exponential backoff, honouring GitHub's Retry-After header.
    """
    s = requests.Session()
    s.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    })
    retry = Retry(
        total=6,
        backoff_factor=2,           # wait 2, 4, 8, 16, 32, 64 s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    return s


# ---------------------------------------------------------------------------
# Hub label
# ---------------------------------------------------------------------------


def hub_label(owner: str, repo: str, hub_subdir: str | None) -> str:
    """Return the canonical hub identifier used in hub_stats_summary.csv."""
    return f"{owner}/{repo}" + (f"/{hub_subdir}" if hub_subdir else "")


# ---------------------------------------------------------------------------
# GitHub metadata
# ---------------------------------------------------------------------------


def get_repo_info(
    session: requests.Session, owner: str, repo: str
) -> tuple[str, str]:
    """Return (pushed_at ISO string, default_branch) for a GitHub repo."""
    response = session.get(f"https://api.github.com/repos/{owner}/{repo}")
    response.raise_for_status()
    data = response.json()
    return data["pushed_at"], data["default_branch"]


def get_tree_sha(
    session: requests.Session, owner: str, repo: str, branch: str
) -> str:
    """Return the root tree SHA for a branch."""
    response = session.get(
        f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
    )
    response.raise_for_status()
    return response.json()["commit"]["commit"]["tree"]["sha"]


# ---------------------------------------------------------------------------
# Git Trees API file listing
# ---------------------------------------------------------------------------


def fetch_subtree_recursive(
    session: requests.Session,
    owner: str,
    repo: str,
    tree_sha: str,
    path_prefix: str = "",
) -> list[dict]:
    """Traverse a tree by fetching each subtree individually (no recursive=1).

    Used as a fallback when the flat recursive response is truncated.
    Returns a list of blob entries, each with at least {"type": "blob", "path": str}.
    """
    response = session.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}"
    )
    response.raise_for_status()

    entries: list[dict] = []
    for item in response.json().get("tree", []):
        full_path = f"{path_prefix}/{item['path']}" if path_prefix else item["path"]
        if item["type"] == "blob":
            entries.append({"type": "blob", "path": full_path})
        elif item["type"] == "tree":
            entries.extend(
                fetch_subtree_recursive(session, owner, repo, item["sha"], full_path)
            )
    return entries


def fetch_full_tree(
    session: requests.Session,
    owner: str,
    repo: str,
    tree_sha: str,
) -> list[dict]:
    """Return all blob entries in a repo's tree.

    Tries the recursive=1 endpoint first (one API call).  Falls back to
    per-subtree traversal when the response is truncated (repos with
    >100 k entries, e.g. large archives).
    """
    response = session.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}",
        params={"recursive": "1"},
    )
    response.raise_for_status()
    data = response.json()

    if not data.get("truncated"):
        return [e for e in data.get("tree", []) if e["type"] == "blob"]

    print(f"  Tree truncated for {owner}/{repo}, using per-subtree traversal")
    return fetch_subtree_recursive(session, owner, repo, tree_sha)


# ---------------------------------------------------------------------------
# File filtering
# ---------------------------------------------------------------------------


def _is_data_file(path: str) -> bool:
    return path.lower().endswith((".csv", ".parquet"))


def list_files_for_directory(
    tree_entries: list[dict],
    directory: str,
    owner: str,
    repo: str,
    default_branch: str,
) -> list[tuple[str, str]]:
    """Return (download_url, source_dir) pairs for CSV/parquet files under directory.

    directory: path relative to repo root, e.g. "model-output" or
               "retrospective-hub/model-output".
    source_dir is always equal to directory for standard (non-archived) paths.
    """
    prefix = f"{directory}/"
    results = []
    for entry in tree_entries:
        path = entry["path"]
        if path.startswith(prefix) and _is_data_file(path):
            url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}"
                f"/{default_branch}/{path}"
            )
            results.append((url, directory))
    return results


def list_files_for_archived_pattern(
    tree_entries: list[dict],
    pattern: str,
    owner: str,
    repo: str,
    default_branch: str,
) -> list[tuple[str, str]]:
    """Return (download_url, source_dir) pairs for files matching a glob pattern.

    pattern uses one '*' per path segment, e.g.:
        "Previous_Rounds/*/model-output"
    matches files under any immediate subdirectory of Previous_Rounds/ whose
    name ends in model-output.

    source_dir is the concrete expanded prefix, e.g.:
        "Previous_Rounds/2025-2026_round_1/model-output"
    """
    parts = pattern.split("/")
    n = len(parts)

    results = []
    for entry in tree_entries:
        path = entry["path"]
        if not _is_data_file(path):
            continue
        path_parts = path.split("/")
        if len(path_parts) <= n:
            continue
        if all(pat == "*" or pat == seg for pat, seg in zip(parts, path_parts)):
            source_dir = "/".join(path_parts[:n])
            url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}"
                f"/{default_branch}/{path}"
            )
            results.append((url, source_dir))
    return results


# ---------------------------------------------------------------------------
# Row counting
# ---------------------------------------------------------------------------


def count_rows_csv(file_url: str, session: requests.Session) -> int:
    """Download a CSV and count data rows (excluding the header)."""
    response = session.get(file_url)
    response.raise_for_status()
    reader = csv.reader(StringIO(response.text))
    try:
        next(reader)  # skip header
    except StopIteration:
        return 0
    return sum(1 for _ in reader)


def count_rows_parquet(file_url: str) -> int:
    """Use DuckDB to read row count from parquet file metadata."""
    with duckdb.connect() as con:
        con.sql("LOAD httpfs;")
        result = con.sql(
            f"SELECT SUM(num_rows) FROM parquet_file_metadata('{file_url}');"
        ).fetchone()
    return result[0] if result else 0


def count_rows(file_url: str, session: requests.Session) -> tuple[str, int]:
    suffix = Path(urlsplit(file_url).path).suffix.lower()
    try:
        count = (
            count_rows_csv(file_url, session)
            if suffix == ".csv"
            else count_rows_parquet(file_url)
        )
    except Exception as e:
        print(f"Error processing {file_url}: {e}")
        count = 0
    return file_url, count


def _count_files(
    files: list[str],
    session: requests.Session,
    label: str,
    canonical_dir: str,
    source_dir: str,
) -> pl.DataFrame:
    """Count rows for a list of file URLs and return a tidy DataFrame.

    canonical_dir: the bucket name ("model-output" or "target-data") used in
                   the summary CSV.
    source_dir:    the actual directory path; equals canonical_dir for standard
                   paths, or the expanded archived path (e.g.
                   "Previous_Rounds/round_1/model-output") for archived dirs.
                   Stored in the parquet for debugging but not in the summary.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(count_rows, f, session) for f in files]

    all_counts: dict[str, int] = defaultdict(int)
    for future in futures:
        url, n = future.result()
        all_counts[url] += n

    df = pl.DataFrame({
        "file": list(all_counts.keys()),
        "row_count": list(all_counts.values()),
    }).with_columns(
        pl.lit(canonical_dir).alias("dir"),
        pl.lit(source_dir).alias("source_dir"),
        pl.lit(label).alias("repo"),
    )
    model_id = (
        pl.col("file").str.extract(r"model-output/([^/]+)/", 1)
        if canonical_dir == "model-output"
        else pl.lit(None).cast(pl.String)
    )
    return df.with_columns(model_id.alias("model_id"))


# ---------------------------------------------------------------------------
# Hub stats fetch
# ---------------------------------------------------------------------------


def fetch_hub_stats(
    session: requests.Session,
    owner: str,
    repo: str,
    hub_subdir: str | None,
    archived_dirs: list[str] | None,
    default_branch: str,
    tree_entries: list[dict],
) -> pl.DataFrame:
    """Count rows for all files in model-output, target-data, and any archived dirs.

    tree_entries: full blob listing from fetch_full_tree().
    """
    label = hub_label(owner, repo, hub_subdir)
    subdir_prefix = f"{hub_subdir}/" if hub_subdir else ""
    frames: list[pl.DataFrame] = []

    # --- standard directories ------------------------------------------------
    for directory in ["model-output", "target-data"]:
        full_dir = f"{subdir_prefix}{directory}"
        file_pairs = list_files_for_directory(
            tree_entries, full_dir, owner, repo, default_branch
        )
        if not file_pairs:
            continue
        files = [url for url, _ in file_pairs]
        frames.append(_count_files(files, session, label, directory, full_dir))

    # --- archived directories -------------------------------------------------
    for pattern in (archived_dirs or []):
        canonical_dir = pattern.rstrip("/").split("/")[-1]
        if canonical_dir not in ("model-output", "target-data"):
            print(
                f"Skipping archived pattern with unrecognised bucket "
                f"'{canonical_dir}': {pattern}"
            )
            continue

        file_pairs = list_files_for_archived_pattern(
            tree_entries, pattern, owner, repo, default_branch
        )
        if not file_pairs:
            print(f"  No files found for archived pattern: {pattern}")
            continue

        # Group by concrete source_dir to preserve per-round breakdown in the parquet.
        by_source: dict[str, list[str]] = defaultdict(list)
        for url, source_dir in file_pairs:
            by_source[source_dir].append(url)

        for source_dir, files in by_source.items():
            print(f"  Found {len(files)} files in archived dir: {source_dir}")
            frames.append(_count_files(files, session, label, canonical_dir, source_dir))

    return pl.concat(frames) if frames else pl.DataFrame()


# ---------------------------------------------------------------------------
# Fetch cache
# ---------------------------------------------------------------------------


def load_fetch_cache(cache_path: Path) -> dict[str, str]:
    """Load {hub_label: pushed_at} mapping from disk, returning {} if absent."""
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return {}


def save_fetch_cache(cache: dict[str, str], cache_path: Path) -> None:
    """Persist the fetch cache to disk."""
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Process one hub
# ---------------------------------------------------------------------------


def process_hub(
    session: requests.Session,
    owner: str,
    repo: str,
    hub_subdir: str | None,
    hub_stats_dir: Path,
    archived_dirs: list[str] | None = None,
    fetch_cache: dict[str, str] | None = None,
    force: bool = False,
) -> Path:
    """Fetch stats for one hub and cache them as a parquet file.

    Skips re-fetching if the hub's pushed_at timestamp matches the cached
    value and the parquet already exists, unless force=True.
    Updates fetch_cache in-place with the new pushed_at after a successful fetch.
    """
    label = hub_label(owner, repo, hub_subdir)
    parquet_path = hub_stats_dir / f"{label.replace('/', '_')}.parquet"
    cache = fetch_cache if fetch_cache is not None else {}

    pushed_at, default_branch = get_repo_info(session, owner, repo)

    if not force and parquet_path.exists() and cache.get(label) == pushed_at:
        print(f"Skipping {label} (no changes since {pushed_at})")
        return parquet_path

    print(f"Fetching stats for {label} (pushed_at={pushed_at})")
    tree_sha = get_tree_sha(session, owner, repo, default_branch)
    tree_entries = fetch_full_tree(session, owner, repo, tree_sha)

    df = fetch_hub_stats(
        session, owner, repo, hub_subdir, archived_dirs, default_branch, tree_entries
    )
    df.write_parquet(parquet_path)
    cache[label] = pushed_at
    return parquet_path


# ---------------------------------------------------------------------------
# Summary CSV
# ---------------------------------------------------------------------------


def write_summary_csv(hub_stats_dir: Path, summary_path: Path) -> None:
    """Aggregate all per-hub parquets into hub_stats_summary.csv."""
    parquet_glob = str(hub_stats_dir / "*.parquet")
    try:
        hub_stats = pl.scan_parquet(parquet_glob, missing_columns="insert").collect()
    except Exception:
        print(f"No parquet files found in {hub_stats_dir}, skipping summary.")
        return

    summary = (
        hub_stats.select(["repo", "dir", "row_count"])
        .filter(pl.col("dir").is_in(["model-output", "target-data"]))
        .group_by("repo", "dir")
        .sum()
        .sort(by=[pl.col("repo").str.to_lowercase(), pl.col("dir")])
    )
    summary.write_csv(summary_path)
    print(f"Saved {summary_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Update hub row-count statistics.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch all hubs regardless of cached pushed_at timestamps.",
    )
    args = parser.parse_args()

    try:
        token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    base_dir = Path(__file__).resolve().parents[1]
    hubs_json = base_dir / "output" / "hubs.json"
    hub_stats_dir = base_dir / "output" / "hub_stats"
    summary_path = base_dir / "output" / "hub_stats_summary.csv"
    cache_path = hub_stats_dir / "fetch_cache.json"
    hub_stats_dir.mkdir(parents=True, exist_ok=True)

    with duckdb.connect() as con:
        con.sql("INSTALL httpfs;")

    session = make_session(token)

    with open(hubs_json) as f:
        hubs = json.load(f)

    fetch_cache = load_fetch_cache(cache_path)

    for hub in hubs.get("hubs", []):
        process_hub(
            session,
            hub["org"],
            hub["repo"],
            hub.get("hub_subdir"),
            hub_stats_dir,
            hub.get("archived_dirs"),
            fetch_cache,
            force=args.force,
        )
        # Save after each hub so partial progress survives a crash or timeout.
        save_fetch_cache(fetch_cache, cache_path)

    write_summary_csv(hub_stats_dir, summary_path)

    last_updated_path = base_dir / "output" / "hub_stats_last_updated.txt"
    last_updated_path.write_text(datetime.date.today().isoformat())


if __name__ == "__main__":
    main()
