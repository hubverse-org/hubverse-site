#!/usr/bin/env bash
#
# Report Hub Model Counts
#
# This script queries the GitHub API for the number of models in each hub and
# reports whether the count differs from the value stored in the file.
#
# USAGE:
#   bash scripts/report_model_counts.sh [file]
#
# ARGUMENTS:
#
#   file  path to the active hubs file. This defaults to
#         `_data/active-hubs.qmd` and assumes you are working in the
#         current working directory.

if ! command -v yq &> /dev/null; then
  echo "This script uses the 'yq' program."
  echo "Installation Instructions: https://github.com/mikefarah/yq/#install"
  exit 1
fi
if ! command -v gh &> /dev/null; then
  echo "This script uses GitHub CLI"
  echo "Installation Instructions: https://cli.github.com"
  exit 1
fi

hub_file="${1:-_data/active-hubs.qmd}"

# Build the GitHub API path for a hub's model-output directory.
# Handles subdirectory hubs stored as "owner/repo/tree/branch/subdir".
model_output_api_path() {
  local repo="${1%/}"
  if [[ "$repo" == */tree/* ]]; then
    local base="${repo%%/tree/*}"
    local rest="${repo#*/tree/*/}"
    echo "/repos/${base}/contents/${rest}/model-output"
  else
    echo "/repos/${repo}/contents/model-output"
  fi
}

selector='[.[] | select((.type == "dir"))] | length'
re='^[0-9]+$'

mapfile -t hubs < <(yq --front-matter=extract '.hubs | to_entries[] | .key as $org | .value.hubs[] | .repo // ($org + ": " + .name)' "${hub_file}")
mapfile -t counts < <(yq --front-matter=extract '.hubs[].hubs[] | .count // 0' "${hub_file}")

for i in "${!hubs[@]}"; do
  hub="${hubs[$i]%/}"
  current="${counts[$i]}"
  n=$(gh api "$(model_output_api_path "${hub}")" --jq "$selector" 2>/dev/null)
  if [[ "${n}" =~ $re && "${n}" -gt 0 ]]; then
    echo "${hub}: ${n} models - updated"
  else
    echo "${hub}: ${current} models - not updated"
  fi
done
