#!/usr/bin/env bats

setup() {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi
  mkdir -p "${BATS_TEST_TMPDIR}/output"
  export WARNINGS_FILE="${BATS_TEST_TMPDIR}/output/hub_stats_warnings.md"
  # Redirect output file inside script by pointing output/ to tmp dir
  export OLDPWD="$PWD"
  cd "${BATS_TEST_TMPDIR}"
  mkdir -p output
}

teardown() {
  cd "$OLDPWD"
}

@test "appends warning when model count decreases" {
  local current="${BATS_TEST_DIRNAME}/fixtures/example_active-hubs_fewer_models.qmd"
  local previous="${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"

  # example_active-hubs_fewer_models has smhet count=8; example_active-hubs has smhet count=0
  # So smhet goes 0 → 8 (increase, no warning).
  # Swap roles: use fewer_models as previous (smhet=8) and current as the file
  # where smhet=0, to test a genuine decrease.
  local hub_file="${BATS_TEST_TMPDIR}/current.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  run bash "${BATS_TEST_DIRNAME}/../scripts/check_model_counts.sh" \
    "$hub_file" \
    "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs_fewer_models.qmd"

  [ "$status" -eq 0 ]
  [[ "$output" == *"Model count warnings appended"* ]]

  # Warning file should mention the hub that decreased (smhet: 8 → 0)
  [ -f output/hub_stats_warnings.md ]
  grep -q "smhet/example-scenario-modeling-hub" output/hub_stats_warnings.md
  grep -q "8" output/hub_stats_warnings.md
}

@test "no warning when all counts stay the same" {
  local hub_file="${BATS_TEST_TMPDIR}/current.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  run bash "${BATS_TEST_DIRNAME}/../scripts/check_model_counts.sh" \
    "$hub_file" \
    "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"

  [ "$status" -eq 0 ]
  [[ "$output" == *"No model count decreases detected"* ]]
  [ ! -f output/hub_stats_warnings.md ] || ! grep -q "Model count decreases" output/hub_stats_warnings.md
}

@test "no warning when count increases" {
  local hub_file="${BATS_TEST_TMPDIR}/current.qmd"
  # current has smhet count=8 (higher than previous 0)
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs_fewer_models.qmd" "$hub_file"

  run bash "${BATS_TEST_DIRNAME}/../scripts/check_model_counts.sh" \
    "$hub_file" \
    "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"

  [ "$status" -eq 0 ]
  [[ "$output" == *"No model count decreases detected"* ]]
  [ ! -f output/hub_stats_warnings.md ] || ! grep -q "Model count decreases" output/hub_stats_warnings.md
}

@test "appends to existing warnings file without overwriting" {
  local hub_file="${BATS_TEST_TMPDIR}/current.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  echo "## Existing row-count warning" > output/hub_stats_warnings.md

  run bash "${BATS_TEST_DIRNAME}/../scripts/check_model_counts.sh" \
    "$hub_file" \
    "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs_fewer_models.qmd"

  [ "$status" -eq 0 ]
  grep -q "Existing row-count warning" output/hub_stats_warnings.md
  grep -q "smhet/example-scenario-modeling-hub" output/hub_stats_warnings.md
}
