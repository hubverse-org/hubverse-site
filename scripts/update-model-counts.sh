#!/usr/bin/env bash

hub_file="${1:-community/_active-hubs.qmd}"
mapfile -t hubs < <(yq --front-matter=extract '.hubs[].hubs[] | .repo' "${hub_file}")
for hub in "${hubs[@]}"; do
  n=$(gh api "/repos/${hub}/contents/model-output" --jq '[.[] | select((.type == "dir"))] | length')
  if [[ $(grep -c '^\d*$' <<< $n) -gt 0 ]]; then
  echo "${hub} has ${n:-no} models"
  count="${n}"
  yq -i --front-matter=process '
  with(.hubs[].hubs[];
    select(.repo == "'"${hub}"'") | .count |= '"${count}"')
  ' "${hub_file}"
  else
  echo "${hub} has an unknown number of models"
  count="missing"
  fi
done


