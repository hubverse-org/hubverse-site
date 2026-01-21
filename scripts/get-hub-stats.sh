#!/usr/bin/env bash

hub=${1}
thing=${2:-tasks}
key=${3:-targets}

branch="$(gh api /repos/${hub} --jq .default_branch)"

tasks="https://raw.githubusercontent.com/${hub}/refs/heads/${branch}/hub-config/${thing}.json"

tmp=$(mktemp)
touch $tmp
curl -sSL -o $tmp $tasks
if [ $key == "targets" ]; then
n=$(cat $tmp | jq '[.rounds[0].model_tasks[].target_metadata[]] | length')
echo 
echo "${n} targets for ${hub}"
echo "=========================================================================="
cat $tmp | jq '[.rounds[0].model_tasks[].target_metadata[] | {id: .target_id, name: .target_name, type: .target_type, desc: .description, unit: .time_unit}]' | yq -P -oy
fi

if [ $key == "aws" ]; then
cat $tmp | jq '.cloud.host' | yq -P -oy
fi

