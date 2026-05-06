"""Get row counts for hub model-output and target-data files.

Reads output/hubs.json, counts rows in each hub's model-output and
target-data directories via the GitHub API, and writes a summary CSV
to output/hub_stats_summary.csv.

Intermediate per-hub results are cached as parquet files in
output/hub_stats/ so that re-runs can skip hubs that have already
been processed locally. The parquet files are not committed to the
repo; only hub_stats_summary.csv is tracked.

Notes
-----
Requires a GITHUB_TOKEN environment variable with read access to
public repositories.

Assumptions
-----------
1. Hub repositories are public and hosted on GitHub.
2. Model output files live in a directory named "model-output".
3. Target data files live in a directory named "target-data".
4. Files are either CSV or parquet format.
5. No two hubs share the same repository name + subdir combination.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb",
#   "polars",
#   "requests",
# ]
# ///

import concurrent.futures
import csv
import json
import os
from collections import defaultdict
from io import StringIO
from pathlib import Path
from urllib.parse import quote, urlsplit

import duckdb
import polars as pl
import requests

# Set > 0 to cap files per directory (useful for local testing).
FILE_COUNT = 0


def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    })
    return s


def hub_label(owner: str, repo: str, hub_subdir: str | None) -> str:
    """Return the canonical hub identifier used in hub_stats_summary.csv."""
    return f"{owner}/{repo}" + (f"/{hub_subdir}" if hub_subdir else "")


def list_files_in_directory(
    session: requests.Session,
    owner: str,
    repo: str,
    directory: str,
) -> list[str]:
    """Return download URLs for all CSV/parquet files in a GitHub directory."""
    url: str | None = (
        f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(directory)}"
    )
    files: list[str] = []
    while url:
        response = session.get(url)
        if response.status_code == 404:
            print(f"Not found: {url}")
            break
        if response.status_code == 403:
            print(f"Access denied or directory too large, skipping: {url}")
            break
        response.raise_for_status()
        for item in response.json():
            if item["type"] == "file" and item["download_url"].lower().endswith(
                (".csv", ".parquet")
            ):
                files.append(item["download_url"])
            elif item["type"] == "dir":
                files.extend(
                    list_files_in_directory(session, owner, repo, item["path"])
                )
            if FILE_COUNT > 0 and len(files) >= FILE_COUNT:
                break
        url = response.links.get("next", {}).get("url")
    return files


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


def fetch_hub_stats(
    session: requests.Session,
    owner: str,
    repo: str,
    hub_subdir: str | None,
) -> pl.DataFrame:
    """Fetch row counts for all files in model-output and target-data."""
    label = hub_label(owner, repo, hub_subdir)
    print(f"Getting stats for {label}")
    subdir_prefix = f"{hub_subdir}/" if hub_subdir else ""
    frames: list[pl.DataFrame] = []

    for directory in ["model-output", "target-data"]:
        full_dir = f"{subdir_prefix}{directory}"
        files = list_files_in_directory(session, owner, repo, full_dir)
        if not files:
            continue

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(count_rows, f, session) for f in files]

        all_counts: dict[str, int] = defaultdict(int)
        for future in futures:
            url, n = future.result()
            all_counts[url] += n

        df = pl.DataFrame({
            "file": list(all_counts.keys()),
            "row_count": list(all_counts.values()),
        }).with_columns(
            pl.lit(directory).alias("dir"),
            pl.lit(label).alias("repo"),
        )
        model_id = (
            pl.col("file").str.extract(r"model-output/([^/]+)/", 1)
            if directory == "model-output"
            else pl.lit(None).cast(pl.String)
        )
        df = df.with_columns(model_id.alias("model_id"))
        frames.append(df)

    return pl.concat(frames) if frames else pl.DataFrame()


def process_hub(
    session: requests.Session,
    owner: str,
    repo: str,
    hub_subdir: str | None,
    hub_stats_dir: Path,
) -> Path:
    """Fetch stats for one hub and cache them as a parquet file."""
    df = fetch_hub_stats(session, owner, repo, hub_subdir)
    label = hub_label(owner, repo, hub_subdir)
    parquet_path = hub_stats_dir / f"{label.replace('/', '_')}.parquet"
    df.write_parquet(parquet_path)
    return parquet_path


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


def main() -> None:
    try:
        token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    base_dir = Path(__file__).resolve().parents[1]
    hubs_json = base_dir / "output" / "hubs.json"
    hub_stats_dir = base_dir / "output" / "hub_stats"
    summary_path = base_dir / "output" / "hub_stats_summary.csv"
    hub_stats_dir.mkdir(parents=True, exist_ok=True)

    with duckdb.connect() as con:
        con.sql("INSTALL httpfs;")

    session = make_session(token)

    with open(hubs_json) as f:
        hubs = json.load(f)

    for hub in hubs.get("hubs", []):
        process_hub(session, hub["org"], hub["repo"], hub.get("hub_subdir"), hub_stats_dir)

    write_summary_csv(hub_stats_dir, summary_path)


if __name__ == "__main__":
    main()
