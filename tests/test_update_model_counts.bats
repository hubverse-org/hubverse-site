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
  [[ "$output" == *"smhet/example-scenario-modeling-hub has an unknown number of models"* ]]

  local hubverse_org_count
  hubverse_org_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "hubverse-org/example-complex-forecast-hub") | .count' "$hub_file")
  [ "$hubverse_org_count" = "2" ]

  local smhet_count
  smhet_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "smhet/example-scenario-modeling-hub") | .count' "$hub_file")
  [ "$smhet_count" = "0" ]
}

