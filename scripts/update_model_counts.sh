#!/usr/bin/env bash
#
# Update Hub Model Counts
#
# This script will update the YAML header of _active-hubs.qmd by querying the
# GitHub API
#
# USAGE:
#   bash scripts/update_model_counts.sh [file]
#
# ARGUMENTS:
#
#   file  path to the active hubs file. This defaults to
#         `community/_active-hubs.qmd` and assumes you are working in the
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

# grab the hub file or fallback to the default
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

# Count model subdirectories across an archived glob pattern like
# "Previous_Rounds/*/model-output". Ignores patterns not ending in model-output.
# Expands the single '*' by listing the parent directory, then counts subdirs
# in each matched path using the GitHub Contents API.
count_archived_model_output() {
  local repo="${1%/}"
  local pattern="$2"

  # Only count patterns that end in model-output
  [[ "${pattern}" != */model-output ]] && echo 0 && return

  local prefix="${pattern%%\**}"   # e.g. "Previous_Rounds/"
  local suffix="${pattern##*\*}"   # e.g. "/model-output"
  prefix="${prefix%/}"             # strip trailing slash

  local total=0
  local round n
  while IFS= read -r round; do
    [[ -z "${round}" ]] && continue
    n=$(gh api "/repos/${repo}/contents/${prefix}/${round}${suffix}" \
          --jq '[.[] | select(.type=="dir")] | length' 2>/dev/null)
    if [[ "${n}" =~ ^[0-9]+$ ]]; then
      total=$((total + n))
    fi
  done < <(gh api "/repos/${repo}/contents/${prefix}" \
             --jq '.[] | select(.type=="dir") | .name' 2>/dev/null)

  echo "${total}"
}

# get array of hub repo locations from the file
mapfile -t hubs < <(yq --front-matter=extract '.hubs[].hubs[] | .repo' "${hub_file}")

selector='[.[] | select((.type == "dir"))] | length'
re='^[0-9]+$'
for hub in "${hubs[@]}"; do
  # 1. Count subdirectories in the root model-output (may be 0 if data has moved
  #    to archived rounds).
  n=$(gh api "$(model_output_api_path "${hub}")" --jq "$selector" 2>/dev/null)
  [[ ! "${n}" =~ $re ]] && n=0

  # 2. Add counts from any archived model-output patterns defined in archived_dirs.
  while IFS= read -r pattern; do
    [[ -z "${pattern}" ]] && continue
    extra=$(count_archived_model_output "${hub}" "${pattern}")
    if [[ "${extra}" =~ $re ]]; then
      n=$((n + extra))
    fi
  done < <(yq --front-matter=extract \
    '.hubs[].hubs[] | select(.repo == "'"${hub%/}"'") | .archived_dirs[]?' \
    "${hub_file}" 2>/dev/null)

  if [[ "${n}" -gt 0 ]]; then
    echo "${hub%/} has ${n} models"
    # 3. Update the count in the frontmatter.
    yq -i --front-matter=process '
    with(.hubs[].hubs[];
      select(.repo == "'"${hub%/}"'") | .count |= '"${n}"'
    )' "${hub_file}"
  else
    existing=$(yq --front-matter=extract \
      '.hubs[].hubs[] | select(.repo == "'"${hub%/}"'") | .count' \
      "${hub_file}" 2>/dev/null)
    echo "${hub%/}: could not determine model count, keeping existing value (${existing:-unknown})"
  fi
done
