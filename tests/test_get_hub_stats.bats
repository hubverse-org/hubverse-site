#!/usr/bin/env bats

setup() {
  local stubdir="${BATS_TEST_DIRNAME}/stubs"

  export GH_BIN="${stubdir}/gh"
  export CURL_BIN="${stubdir}/curl"
  export CURL_FIXTURE="${BATS_TEST_DIRNAME}/fixtures/example_tasks.json"
}

@test "default run prints targets summary" {
  run scripts/get-hub-stats.sh example/hub

  [ "$status" -eq 0 ]
  [[ "$output" == *"2 targets for example/hub"* ]]

  cat <<'EOF' >"$BATS_TEST_TMPDIR/expected"
2 targets for example/hub
==========================================================================
- id: accuracy
  name: Accuracy
  type: metric
  desc: Accuracy on validation split
  unit: seconds
- id: latency
  name: Latency
  type: metric
  desc: 99th percentile latency
  unit: milliseconds
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

