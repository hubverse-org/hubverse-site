#!/usr/bin/env bats

setup() {
  local stubdir="${BATS_TEST_DIRNAME}/stubs"
  export PATH="${stubdir}:${PATH}"
}

@test "updates counts when gh returns model directories" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/active-hubs.qmd" "$hub_file"

  export GH_COUNT_foo_bar=3
  export GH_COUNT_baz_qux=5

  run scripts/update-model-counts.sh "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"foo/bar has 3 models"* ]]
  [[ "$output" == *"baz/qux has 5 models"* ]]

  local foo_count
  foo_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "foo/bar") | .count' "$hub_file")
  [ "$foo_count" = "3" ]

  local baz_count
  baz_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "baz/qux") | .count' "$hub_file")
  [ "$baz_count" = "5" ]
}

@test "leaves count unchanged when gh result is not positive" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  local hub_file="${BATS_TEST_TMPDIR}/active-hubs.qmd"
  cp "${BATS_TEST_DIRNAME}/fixtures/active-hubs.qmd" "$hub_file"

  export GH_COUNT_foo_bar=2
  export GH_COUNT_baz_qux="oops"

  run scripts/update-model-counts.sh "$hub_file"

  [ "$status" -eq 0 ]
  [[ "$output" == *"foo/bar has 2 models"* ]]
  [[ "$output" == *"baz/qux has an unknown number of models"* ]]

  local foo_count
  foo_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "foo/bar") | .count' "$hub_file")
  [ "$foo_count" = "2" ]

  local baz_count
  baz_count=$(yq --front-matter=extract '.hubs[].hubs[] | select(.repo == "baz/qux") | .count' "$hub_file")
  [ "$baz_count" = "0" ]
}

