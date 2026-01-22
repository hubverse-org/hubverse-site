#!/usr/bin/env bats

setup() {
  local stubdir="${BATS_TEST_DIRNAME}/stubs"

  HUB_PATH="example-org/example-hub"

  export GH_BIN="${stubdir}/gh"
  export CURL_BIN="${stubdir}/curl"
  export CURL_FIXTURE="${BATS_TEST_DIRNAME}/fixtures/example_tasks.json"

  if ! command -v yq >/dev/null; then
    skip "yq is required for get_hub_stats tests"
  fi

}

@test "default run prints targets summary" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi

  run "${BATS_TEST_DIRNAME}/../scripts/get_hub_stats.sh" "$HUB_PATH"

  [ "$status" -eq 0 ]

  header="2 targets for ${HUB_PATH}"
  [[ "$output" == *"$header"* ]]

  cat <<EOF >"$BATS_TEST_TMPDIR/expected"
$header
==========================================================================
- id: wk inc hosp
  name: Weekly incident hospitalizations
  type: continuous
  desc: Hospitalization counts on a weekly basis
  unit: week
- id: clade prop
  name: Daily nowcasted clade proportions
  type: compositional
  desc: Daily nowcasted clade proportions among all cases
  unit: day
EOF

  printf '%s\n' "$output" | sed '1d' > "$BATS_TEST_TMPDIR/actual"
  diff -u "$BATS_TEST_TMPDIR/expected" "$BATS_TEST_TMPDIR/actual"
}

@test "aws metadata prints host information" {
  if ! command -v yq >/dev/null; then
  skip "yq must be installed for this test"
  fi

  local admin_fixture="${BATS_TEST_DIRNAME}/fixtures/example_admin.json"

  CURL_FIXTURE="$admin_fixture"   # overrides the stub fixture
  run "${BATS_TEST_DIRNAME}/../scripts/get_hub_stats.sh" "$HUB_PATH" admin aws

  [ "$status" -eq 0 ]

  cat <<'EOF' >"$BATS_TEST_TMPDIR/expected"
name: aws
storage_service: s3
storage_location: example-complex-forecast-hub
EOF

  printf '%s\n' "$output" >"$BATS_TEST_TMPDIR/actual"
  diff -u "$BATS_TEST_TMPDIR/expected" "$BATS_TEST_TMPDIR/actual"
}

