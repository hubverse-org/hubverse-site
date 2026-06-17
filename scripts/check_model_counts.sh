#!/usr/bin/env bash
#
# Check for model count decreases in _data/active-hubs.qmd.
#
# Compares the current counts against the committed HEAD version (or a
# reference file supplied as the second argument).  Any hub whose count
# decreased is appended as a warning section to output/hub_stats_warnings.md
# so that it appears in the same PR comment as row-count regressions.
# Always exits 0 (non-blocking).
#
# USAGE:
#   bash scripts/check_model_counts.sh [hub_file] [previous_hub_file]
#
# ARGUMENTS:
#   hub_file           path to active-hubs.qmd (default: _data/active-hubs.qmd)
#   previous_hub_file  path to a reference file for comparison; if omitted,
#                      the committed HEAD version of hub_file is used

if ! command -v yq &> /dev/null; then
  echo "This script uses the 'yq' program."
  echo "Installation Instructions: https://github.com/mikefarah/yq/#install"
  exit 1
fi

hub_file="${1:-_data/active-hubs.qmd}"
warnings_file="output/hub_stats_warnings.md"

extract_counts() {
  yq --front-matter=extract \
    '.hubs[].hubs[] | .repo + " " + (.count // 0 | tostring)' \
    "$1" 2>/dev/null
}

# Resolve the previous version.
if [[ -n "${2:-}" ]]; then
  prev_file="$2"
  _tmp_prev=""
else
  _tmp_prev=$(mktemp)
  git show HEAD:"${hub_file}" > "${_tmp_prev}" 2>/dev/null || true
  prev_file="${_tmp_prev}"
fi

declare -A current previous

while IFS=' ' read -r repo count; do
  [[ -z "${repo}" || "${repo}" == "null" || "${repo}" == "~" ]] && continue
  current["${repo}"]="${count}"
done < <(extract_counts "${hub_file}")

while IFS=' ' read -r repo count; do
  [[ -z "${repo}" || "${repo}" == "null" || "${repo}" == "~" ]] && continue
  previous["${repo}"]="${count}"
done < <(extract_counts "${prev_file}")

[[ -n "${_tmp_prev}" ]] && rm -f "${_tmp_prev}"

warnings=()
for repo in "${!previous[@]}"; do
  old="${previous[${repo}]}"
  new="${current[${repo}]:-}"
  [[ -z "${new}" || "${new}" == "null" ]] && continue
  if [[ "${old}" =~ ^[0-9]+$ && "${new}" =~ ^[0-9]+$ && "${new}" -lt "${old}" ]]; then
    warnings+=("| \`${repo}\` | ${old} | ${new} |")
  fi
done

if [[ ${#warnings[@]} -gt 0 ]]; then
  {
    echo ""
    echo "## :warning: Model count decreases"
    echo ""
    echo "The following hubs have fewer models recorded than previously:"
    echo ""
    echo "| Hub | Previous | Current |"
    echo "| --- | -------- | ------- |"
    for w in "${warnings[@]}"; do
      echo "${w}"
    done
    echo ""
    echo "A decrease may indicate teams dropped out, or that the model count"
    echo "could not be fetched for some archived round directories."
  } >> "${warnings_file}"
  echo "Model count warnings appended to ${warnings_file}"
else
  echo "No model count decreases detected."
fi
