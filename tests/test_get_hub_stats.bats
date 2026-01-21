#!/usr/bin/env bats

setup() {
  local stubdir="${BATS_TEST_DIRNAME}/stubs"
  
  HUB_PATH="${BATS_TEST_DIRNAME}/../example/hub"

  export GH_BIN="${stubdir}/gh"
  export CURL_BIN="${stubdir}/curl"
  export CURL_FIXTURE="${BATS_TEST_DIRNAME}/fixtures/example_tasks.json"
}

@test "default run prints targets summary" {
  if ! command -v yq >/dev/null; then
    skip "yq must be installed for this test"
  fi
  
  run "${BATS_TEST_DIRNAME}/../scripts/get-hub-stats.sh" "$hub_path"

  [ "$status" -eq 0 ]
  [[ "$output" == *"2 targets for example/hub"* ]]

  cat <<'EOF' >"$BATS_TEST_TMPDIR/expected"
2 targets for example/hub
==========================================================================
- id: wk inc hosp
  name: incident hospitalizations
  type: continuous
  desc: Hospitalization counts on a weekly basis
  unit: week
- id: death prop
  name: proportion of deaths
  type: compositional
  desc: Daily nowcasted proportion of deaths among all cases
  unit: day
EOF

  # strip the leading blank line emitted by `echo` in the script
  printf '%s\n' "$output" | sed '1d' > "$BATS_TEST_TMPDIR/actual"

  diff -u "$BATS_TEST_TMPDIR/expected" "$BATS_TEST_TMPDIR/actual"
}

@test "aws key prints host information" {
  run scripts/get-hub-stats.sh example/hub tasks aws

  [ "$status" -eq 0 ]
  [ "$output" = "aws://prod.example.internal" ]
}

