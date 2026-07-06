#!/usr/bin/env bats

setup() {
  local stubdir="${BATS_TEST_DIRNAME}/stubs"
  export PATH="${stubdir}:${PATH}"
}

@test "updates counts when gh returns model directories" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/example_active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  export GH_COUNT_hubverse_org_example_complex_forecast_hub=3
  export GH_COUNT_smhet_example_scenario_modeling_hub=5

  run "${BATS_TEST_DIRNAME}/../scripts/update_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"hubverse-org/example-complex-forecast-hub has 3 models"* ]]
  [[ "$output" == *"smhet/example-scenario-modeling-hub has 5 models"* ]]

  local hubverse_org_count
  hubverse_org_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "hubverse-org/example-complex-forecast-hub") | .count' "$hub_file")
  [ "$hubverse_org_count" = "3" ]

  local smhet_count
  smhet_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "smhet/example-scenario-modeling-hub") | .count' "$hub_file")
  [ "$smhet_count" = "5" ]
}

@test "updates counts for subdirectory hubs" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/example_active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  export GH_COUNT_example_subdir_org_monorepo_example_subdir_hub=7

  run "${BATS_TEST_DIRNAME}/../scripts/update_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"example-subdir-org/monorepo/tree/main/example-subdir-hub has 7 models"* ]]

  local count
  count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "example-subdir-org/monorepo/tree/main/example-subdir-hub") | .count' "$hub_file")
  [ "$count" = "7" ]
}

@test "sums model counts across archived round directories" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/example_active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  # Root model-output is empty; two archived rounds each have teams
  export GH_COUNT_example_archived_org_example_archived_hub=0
  export GH_ROUNDS_example_archived_org_example_archived_hub_contents_Previous_Rounds="2024-2025_round_1
2025-2026_round_1"
  export GH_COUNT_example_archived_org_example_archived_hub_Previous_Rounds_2024_2025_round_1=15
  export GH_COUNT_example_archived_org_example_archived_hub_Previous_Rounds_2025_2026_round_1=13

  run "${BATS_TEST_DIRNAME}/../scripts/update_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"example-archived-org/example-archived-hub has 28 models"* ]]

  local count
  count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "example-archived-org/example-archived-hub") | .count' "$hub_file")
  [ "$count" = "28" ]
}

@test "ignores archived_dirs patterns that do not end in model-output" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/example_active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  export GH_COUNT_example_archived_org_example_archived_hub=0
  export GH_ROUNDS_example_archived_org_example_archived_hub_contents_Previous_Rounds="2024-2025_round_1"
  export GH_COUNT_example_archived_org_example_archived_hub_Previous_Rounds_2024_2025_round_1=10

  run "${BATS_TEST_DIRNAME}/../scripts/update_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  # target-data pattern should be ignored; only the model-output round contributes
  [[ "$output" == *"example-archived-org/example-archived-hub has 10 models"* ]]

  local count
  count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "example-archived-org/example-archived-hub") | .count' "$hub_file")
  [ "$count" = "10" ]
}

@test "preserves existing count and logs message when model count cannot be determined" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/example_active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  # No GH_COUNT set for smhet hub → count cannot be determined
  export GH_COUNT_hubverse_org_example_complex_forecast_hub=4
  unset GH_COUNT_smhet_example_scenario_modeling_hub 2>/dev/null || true
  export GH_COUNT_DEFAULT=0

  run "${BATS_TEST_DIRNAME}/../scripts/update_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"smhet/example-scenario-modeling-hub: could not determine model count, keeping existing value"* ]]

  # smhet count stays at its original value (0 from fixture)
  local smhet_count
  smhet_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "smhet/example-scenario-modeling-hub") | .count' "$hub_file")
  [ "$smhet_count" = "0" ]
}

@test "skips hubs with null or empty repo" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/example_active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  export GH_COUNT_hubverse_org_example_complex_forecast_hub=3

  run "${BATS_TEST_DIRNAME}/../scripts/update_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  # null/empty repos should not appear in output at all
  [[ "$output" != *"null:"* ]]
  [[ "$output" != *"null has"* ]]
}

@test "leaves count unchanged when gh result is not positive" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/example_active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd" "$hub_file"

  export GH_COUNT_hubverse_org_example_complex_forecast_hub=2
  export GH_COUNT_smhet_example_scenario_modeling_hub="oops"

  run "${BATS_TEST_DIRNAME}/../scripts/update_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"hubverse-org/example-complex-forecast-hub has 2 models"* ]]
  [[ "$output" == *"smhet/example-scenario-modeling-hub: could not determine model count"* ]]

  local hubverse_org_count
  hubverse_org_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "hubverse-org/example-complex-forecast-hub") | .count' "$hub_file")
  [ "$hubverse_org_count" = "2" ]

  local smhet_count
  smhet_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "smhet/example-scenario-modeling-hub") | .count' "$hub_file")
  [ "$smhet_count" = "0" ]
}

