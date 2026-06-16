"""Compare the freshly generated hub_stats_summary.csv against the last
committed version and report any regressions.

Regressions are:
  - A repo/dir row that was present in the committed CSV but is absent in the new one.
  - A repo/dir row whose row_count decreased.

Exits 0 in all cases (non-blocking); prints a structured warning to stdout
so that the GitHub Actions step can capture it and post it as a PR comment.

Usage
-----
    python scripts/check_hub_stats.py [--summary PATH] [--committed PATH]

If --committed is not given the script uses ``git show HEAD:output/hub_stats_summary.csv``
to obtain the baseline.
"""

import argparse
import csv
import subprocess
import sys
from io import StringIO
from pathlib import Path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Path to the newly generated hub_stats_summary.csv (default: output/hub_stats_summary.csv relative to repo root)",
    )
    parser.add_argument(
        "--committed",
        type=Path,
        default=None,
        help="Path to the baseline CSV. If omitted, read from HEAD via git.",
    )
    return parser.parse_args(argv)


def read_csv_as_dict(text: str) -> dict[tuple[str, str], int]:
    """Parse CSV text into {(repo, dir): row_count}."""
    reader = csv.DictReader(StringIO(text))
    return {(row["repo"], row["dir"]): int(row["row_count"]) for row in reader}


def load_committed_csv(summary_path: Path) -> dict[tuple[str, str], int] | None:
    """Load the committed version of hub_stats_summary.csv via git show."""
    # Make the path relative to the repo root for git show
    try:
        repo_root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
        )
        rel = summary_path.resolve().relative_to(repo_root)
        result = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("WARNING: could not read committed hub_stats_summary.csv via git — skipping regression check.")
            return None
        return read_csv_as_dict(result.stdout)
    except Exception as e:
        print(f"WARNING: git show failed ({e}) — skipping regression check.")
        return None


def check(
    committed: dict[tuple[str, str], int],
    current: dict[tuple[str, str], int],
) -> list[str]:
    """Return a list of warning lines, empty if no regressions found."""
    warnings: list[str] = []

    for key, old_count in sorted(committed.items()):
        repo, directory = key
        if key not in current:
            warnings.append(
                f"  - **DISAPPEARED**: `{repo}` / `{directory}` "
                f"(was {old_count:,} rows — now absent)"
            )
        else:
            new_count = current[key]
            if new_count < old_count:
                diff = old_count - new_count
                pct = 100 * diff / old_count if old_count else 0
                warnings.append(
                    f"  - **DECREASED**: `{repo}` / `{directory}` "
                    f"{old_count:,} → {new_count:,} (−{diff:,}, −{pct:.1f}%)"
                )

    return warnings


def main(argv=None) -> int:
    args = parse_args(argv)

    base_dir = Path(__file__).resolve().parents[1]
    summary_path = args.summary or (base_dir / "output" / "hub_stats_summary.csv")

    if not summary_path.exists():
        print(f"ERROR: {summary_path} not found — cannot check hub stats.")
        return 0

    with open(summary_path) as f:
        current = read_csv_as_dict(f.read())

    if args.committed:
        with open(args.committed) as f:
            committed = read_csv_as_dict(f.read())
    else:
        committed = load_committed_csv(summary_path)

    if committed is None:
        return 0

    warnings = check(committed, current)

    if not warnings:
        print("hub-stats-check: no regressions detected.")
        # Write an empty marker so the workflow step always has something to read.
        marker = base_dir / "output" / "hub_stats_warnings.md"
        marker.write_text("")
        return 0

    body_lines = [
        "## :warning: Hub stats regression warning",
        "",
        "The following issues were detected when comparing the new "
        "`hub_stats_summary.csv` against the previously committed version.",
        "Please review before merging.",
        "",
    ] + warnings + [
        "",
        "<details><summary>What to do</summary>",
        "",
        "- **DISAPPEARED**: the hub's `model-output` or `target-data` directory "
          "may have been moved or archived upstream. Check the repo and consider "
          "adding an `archived_dirs` entry in `_data/active-hubs.qmd`.",
        "- **DECREASED**: row counts should only increase. A decrease can indicate "
          "a transient API/network error (re-run the workflow) or that files were "
          "removed upstream (investigate before merging).",
        "",
        "</details>",
    ]

    body = "\n".join(body_lines)
    print(body)

    # Write to a file so the workflow step can pick it up.
    marker = base_dir / "output" / "hub_stats_warnings.md"
    marker.write_text(body)
    print(f"\nWarnings written to {marker}")

    return 0  # always exit 0 — non-blocking


if __name__ == "__main__":
    sys.exit(main())
