#!/usr/bin/env bash
#
# Update Hub Model Counts
#
# This script will update the YAML header of _active-hubs.qmd by querying the
# GitHub API 
# 
# USAGE:
#   bash scripts/update-model-counts.sh [file]
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
hub_file="${1:-community/_active-hubs.qmd}"

# get array of hub repo locations from the file
mapfile -t hubs < <(yq --front-matter=extract '.hubs[].hubs[] | .repo' "${hub_file}")

selector='[.[] | select((.type == "dir"))] | length'
re='^[0-9]+$'
for hub in "${hubs[@]}"; do
  # 1. Use the GitHub API to count the number of directories in `model-output`
  n=$(gh api "/repos/${hub%/}/contents/model-output" --jq "$selector")
  if [[ "${n}" =~ $re && "${n}" -gt 0 ]]; then
    echo "${hub%/} has ${n} models"
    # 2. Use yq to update that number in the frontmatter
    #    -i                      update file in place
    #    --front-matter=process  process the frontmatter, but leave the rest of
    #      the file in tact
    #
    #    `with`: https://mikefarah.gitbook.io/yq/operators/with
    #    `select`: https://mikefarah.gitbook.io/yq/operators/select
    #    `|` (pipe): https://mikefarah.gitbook.io/yq/operators/pipe
    #    `|=` (assignment): https://mikefarah.gitbook.io/yq/operators/assign-update
    yq -i --front-matter=process '
    with(.hubs[].hubs[];
      select(.repo == "'"${hub%/}"'") | .count |= '"${n}"'
    )' "${hub_file}"
  else
    echo "${hub} has an unknown number of models"
    count="missing"
  fi
done


