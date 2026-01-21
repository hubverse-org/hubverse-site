#!/usr/bin/env bash
set -euo pipefail

# -----------------------
# Inputs
# -----------------------
hub=${1}
thing=${2:-tasks}
key=${3:-targets}

# -----------------------
# Allow dependency injection (for testing)
# -----------------------
GH=${GH:-gh}
CURL=${CURL:-curl}
JQ=${JQ:-jq}
YQ=${YQ:-yq}

# -----------------------
# Get default branch
# -----------------------
branch="$($GH api /repos/${hub} --jq .default_branch)"

# -----------------------
# Build URL
# -----------------------
tasks="https://raw.githubusercontent.com/${hub}/refs/heads/${branch}/hub-config/${thing}.json"

# -----------------------
# Fetch JSON to temp file
# -----------------------
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

$CURL -sSL -o "$tmp" "$tasks"

# -----------------------
# Targets output
# -----------------------
if [ "$key" = "targets" ]; then
  n=$(cat "$tmp" | $JQ '[.rounds[0].model_tasks[].target_metadata[]] | length')

  echo
  echo "${n} targets for ${hub}"
  echo "=========================================================================="

  cat "$tmp" \
    | $JQ '[.rounds[0].model_tasks[].target_metadata[]
      | {
          id: .target_id,
          name: .target_name,
          type: .target_type,
          desc: .description,
          unit: .time_unit
        }
    ]' \
    | $YQ -P -oy
fi

# -----------------------
# AWS output
# -----------------------
if [ "$key" = "aws" ]; then
  cat "$tmp" | $JQ '.cloud.host' | $YQ -P -oy
fi
