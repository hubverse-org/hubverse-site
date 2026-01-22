#!/usr/bin/env bash

GH_BIN="${GH_BIN:-gh}"
CURL_BIN="${CURL_BIN:-curl}"

hub=${1}
thing=${2:-tasks}
key=${3:-targets}

branch="$("$GH_BIN" api "/repos/${hub}" --jq .default_branch)"

tasks="https://raw.githubusercontent.com/${hub}/refs/heads/${branch}/hub-config/${thing}.json"

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT    # optional cleanup improvement
"$CURL_BIN" -sSL -o "$tmp" "$tasks"

if [ "$key" == "targets" ]; then
  n=$(jq '[.rounds[0].model_tasks[].target_metadata[]] | length' "$tmp")
  echo
  echo "${n} targets for ${hub}"
  echo "=========================================================================="
  jq '[.rounds[0].model_tasks[].target_metadata[] | {id: .target_id, name: .target_name, type: .target_type, desc: .description, unit: .time_unit}]' "$tmp" | yq -P -oy
fi

if [ "$key" == "aws" ]; then
  jq '.cloud.host' "$tmp" | yq -P -oy
fi

