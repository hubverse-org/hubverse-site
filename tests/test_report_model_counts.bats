#!/usr/bin/env bats

setup() {
  local stubdir="${BATS_TEST_DIRNAME}/stubs"
  export PATH="${stubdir}:${PATH}"
}

@test "reports updated counts when gh returns model directories" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"

  export GH_COUNT_hubverse_org_example_complex_forecast_hub=3
  export GH_COUNT_smhet_example_scenario_modeling_hub=5

  run "${BATS_TEST_DIRNAME}/../scripts/report_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"hubverse-org/example-complex-forecast-hub: 3 models - updated"* ]]
  [[ "$output" == *"smhet/example-scenario-modeling-hub: 5 models - updated"* ]]
}

@test "reports not-updated with stored count when gh result is not positive" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"

  export GH_COUNT_hubverse_org_example_complex_forecast_hub=3
  export GH_COUNT_smhet_example_scenario_modeling_hub="oops"

  run "${BATS_TEST_DIRNAME}/../scripts/report_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"hubverse-org/example-complex-forecast-hub: 3 models - updated"* ]]
  [[ "$output" == *"smhet/example-scenario-modeling-hub: 0 models - not updated"* ]]
}

@test "reports updated counts for subdirectory hubs" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"

  export GH_COUNT_example_subdir_org_monorepo_example_subdir_hub=7

  run "${BATS_TEST_DIRNAME}/../scripts/report_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"example-subdir-org/monorepo/tree/main/example-subdir-hub: 7 models - updated"* ]]
}

@test "reports not-updated with stored count for subdirectory hubs when gh fails" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"

  export GH_COUNT_example_subdir_org_monorepo_example_subdir_hub="oops"

  run "${BATS_TEST_DIRNAME}/../scripts/report_model_counts.sh" "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"example-subdir-org/monorepo/tree/main/example-subdir-hub: 2 models - not updated"* ]]
}

@test "does not modify the hub file" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_DIRNAME}/fixtures/example_active-hubs.qmd"
  local before after
  before=$(cat "$hub_file")

  export GH_COUNT_hubverse_org_example_complex_forecast_hub=99

  run "${BATS_TEST_DIRNAME}/../scripts/report_model_counts.sh" "$hub_file"

  after=$(cat "$hub_file")
  [ "$before" = "$after" ]
}
