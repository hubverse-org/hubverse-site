# CLAUDE.md — hubverse-site

## Overview

Quarto-based static website for [hubverse.io](https://hubverse.io). Built with
Python scripts for data generation, BASH scripts for hub metadata, and two
GitHub Actions workflows for automated updates.

The live site is **served by GitHub Pages** (published by `publish.yml`).
**Netlify only builds PR deploy previews** (`netlify.toml`, `netlify-build.sh`)
— it does not serve production.

## Commands

```bash
# Run all tests
make test
# or separately:
python -m pytest          # Python tests
bats tests/               # BASH tests

# Generate pre-computed content and render locally
make render               # generate content + quarto render
make preview              # generate content + quarto preview

# Individual generation steps
make contributors         # update community/contributors.md
make models               # update model counts in _data/active-hubs.qmd
make terminology          # update terminology.qmd
make cite                 # update cite.qmd
```

## Repository structure

```
_data/active-hubs.qmd     # SOURCE OF TRUTH for all hub metadata (YAML frontmatter)
scripts/                  # data generation scripts
output/                   # generated files (committed to repo)
  hubs.json               # derived from _data/active-hubs.qmd
  active-hubs-table.csv   # derived from _data/active-hubs.qmd
  hub_stats_summary.csv   # per-hub row counts
  hub_stats/              # per-hub parquet cache + fetch_cache.json
community/hubs.qmd        # hubs page (renders cards + sortable table)
.github/workflows/
  publish.yml             # renders + publishes site on push to main
  update-hub-stats.yml    # weekly row-count + model-count update
tests/
  *.py                    # pytest (Python scripts)
  *.bats                  # bats (BASH scripts)
  fixtures/               # fixture files shared across tests
  stubs/                  # stub executables (gh, curl) for BASH tests
```

## Adding a hub

1. Edit `_data/active-hubs.qmd` — add the hub under the correct org in the
   YAML frontmatter. Required fields: `name`, `repo`. Optional: `insights`,
   `aws`, `archived_dirs`.
2. If adding a **new organization**, also add its slug to the `CATEGORIES` dict
   in `scripts/hub_table.py` (`"Active"`, `"Archival"`, `"Training"`, or
   `"Model Development"`). Without this the org appears as "Other".
3. The `output/` files are regenerated automatically by the workflows — do not
   edit them by hand.

## Key scripts

| Script | Purpose |
|--------|---------|
| `scripts/print_hub_list.py` | Reads `_data/active-hubs.qmd` → writes `output/hubs.json` and `output/active-hubs-table.csv` |
| `scripts/get_hub_stats.py` | Reads `output/hubs.json` → fetches row counts via Git Trees API → writes per-hub parquets + `output/hub_stats_summary.csv` |
| `scripts/check_hub_stats.py` | Compares new `hub_stats_summary.csv` to HEAD → writes `output/hub_stats_warnings.md` |
| `scripts/hub_table.py` | Builds the sortable HTML table for `community/hubs.qmd` |
| `scripts/update_model_counts.sh` | Queries GitHub API for model counts → updates `count:` in `_data/active-hubs.qmd` in-place |
| `scripts/check_model_counts.sh` | Compares model counts to HEAD → appends decreases to `output/hub_stats_warnings.md` |

## Workflows

### `publish.yml`
Triggered on push to `main` and weekly (Fridays). Runs `make contributors
terminology cite`, then renders and publishes to GitHub Pages. `make models`
is intentionally omitted — model counts are updated and committed by the
Update Hub Stats workflow before publish runs, so re-running it would trigger
redundant GitHub API calls and risk rate-limiting.

### `update-hub-stats.yml`
Triggered weekly (Mondays) or manually. Steps:
1. `print_hub_list.py` — regenerate `output/hubs.json`
2. `update_model_counts.sh` — refresh `count:` in `_data/active-hubs.qmd`
3. `get_hub_stats.py` — fetch row counts (skip unchanged hubs via `fetch_cache.json`; use `--force` to re-fetch all)
4. `check_hub_stats.py` + `check_model_counts.sh` — detect regressions
5. Opens a PR with updated data files; posts a warning comment if any counts decreased

## Hub stats details

- Uses the **Git Trees API** (one call per repo) instead of the Contents API,
  which fails silently with 403 for directories > 1000 files.
- For repos with > 100k entries (truncated tree), falls back to per-subtree
  traversal.
- `fetch_cache.json` maps `hub_label → pushed_at`. Hubs whose `pushed_at`
  hasn't changed since the last run are skipped entirely.
- `archived_dirs` in `_data/active-hubs.qmd` supports glob patterns with one
  `*` per segment (e.g. `"Previous_Rounds/*/model-output"`) for hubs that have
  moved data to archive subdirectories.

## Tests

Python tests use `pytest`. BASH tests use [`bats`](https://bats-core.readthedocs.io/).
BASH tests stub out `gh` and `curl` via executables in `tests/stubs/`, controlled
by environment variables (e.g. `GH_COUNT_org_repo=5`).

To add a test for a new BASH script, add a `test_<script>.bats` file and extend
`tests/stubs/gh` if the script makes new types of GitHub API calls.

## Branch / PR conventions

- Feature branches follow `micokoch-<description>` naming.
- The automated hub stats PR always lands on branch `chore/update-hub-stats`.
- Never commit directly to `main`; always go through a PR.
