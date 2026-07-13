#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
BUILD_SCRIPT="$ROOT_DIR/scripts/build-site.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_exists() {
  local path="$1"
  [ -e "$path" ] || fail "expected build artifact: ${path#"$OUTPUT_DIR"/}"
}

assert_absent() {
  local path="$1"
  [ ! -e "$path" ] || fail "unexpected build artifact: ${path#"$OUTPUT_DIR"/}"
}

assert_rejected() {
  local candidate="$1"
  local label="$2"
  local status=0

  : > "$RM_LOG"
  HOME="$FAKE_HOME" RM_LOG="$RM_LOG" PATH="$SAFE_BIN:$ORIGINAL_PATH" \
    "$FAKE_BUILD_SCRIPT" "$candidate" >/dev/null 2>&1 || status=$?

  [ ! -s "$RM_LOG" ] || fail "unsafe output path reached rm before rejection: $label"
  [ "$status" -ne 0 ] || fail "unsafe output path was accepted: $label"
}

[ -x "$BUILD_SCRIPT" ] || fail "missing executable build script: scripts/build-site.sh"

ORIGINAL_PATH="$PATH"
OUTPUT_DIR="$ROOT_DIR/_site"
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/dykj-build-safety.XXXXXX")"
FAKE_REPO="$SANDBOX/repo"
FAKE_HOME="$SANDBOX/home"
SAFE_BIN="$SANDBOX/safe-bin"
RM_LOG="$SANDBOX/rm.log"
FAKE_BUILD_SCRIPT="$FAKE_REPO/scripts/build-site.sh"
UNSAFE_OUTPUT_DIR="$SANDBOX/arbitrary-output"

cleanup() {
  /bin/rm -rf "$SANDBOX"
  /bin/rm -rf "$OUTPUT_DIR"
}

trap cleanup EXIT

/bin/mkdir -p \
  "$FAKE_REPO/scripts" "$FAKE_REPO/css" "$FAKE_REPO/js" \
  "$FAKE_REPO/assets" "$FAKE_HOME" "$SAFE_BIN" "$UNSAFE_OUTPUT_DIR"
/bin/cp "$BUILD_SCRIPT" "$FAKE_BUILD_SCRIPT"
/bin/chmod 755 "$FAKE_BUILD_SCRIPT"

printf '<!doctype html><title>fixture</title>\n' > "$FAKE_REPO/index.html"
printf 'body {}\n' > "$FAKE_REPO/css/style.css"
printf 'void 0;\n' > "$FAKE_REPO/js/main.js"
printf 'fixture\n' > "$FAKE_REPO/assets/placeholder.txt"
printf 'keep me\n' > "$UNSAFE_OUTPUT_DIR/marker"

printf '%s\n' \
  '#!/bin/bash' \
  ': "${RM_LOG:?RM_LOG is required}"' \
  'printf "rm attempted: %s\n" "$*" >> "$RM_LOG"' \
  'exit 97' > "$SAFE_BIN/rm"
/bin/chmod 755 "$SAFE_BIN/rm"

wrapper_status=0
RM_LOG="$RM_LOG" "$SAFE_BIN/rm" --probe >/dev/null 2>&1 || wrapper_status=$?
[ "$wrapper_status" -eq 97 ] || fail "safe rm wrapper returned unexpected status"
[ -s "$RM_LOG" ] || fail "safe rm wrapper did not record its probe"

assert_rejected "$UNSAFE_OUTPUT_DIR" "arbitrary non-empty directory"
[ -e "$UNSAFE_OUTPUT_DIR/marker" ] || fail "rejected arbitrary output directory lost its marker"

assert_rejected "" "empty path"
assert_rejected "/" "filesystem root"
assert_rejected "$FAKE_REPO" "repository root"
assert_rejected "$FAKE_HOME" "home directory"
assert_rejected "$SANDBOX" "repository parent"
assert_rejected "$FAKE_REPO/assets/unsafe" "nested assets directory"

"$BUILD_SCRIPT" "$OUTPUT_DIR"

assert_exists "$OUTPUT_DIR/index.html"
assert_exists "$OUTPUT_DIR/css"
assert_exists "$OUTPUT_DIR/js"
assert_exists "$OUTPUT_DIR/assets"

if [ -e "$ROOT_DIR/.nojekyll" ]; then
  assert_exists "$OUTPUT_DIR/.nojekyll"
fi

for excluded in \
  source docs tests scripts .github node_modules \
  README.md package.json package-lock.json yarn.lock pnpm-lock.yaml; do
  assert_absent "$OUTPUT_DIR/$excluded"
done

printf 'PASS: build artifact contains only deployable site inputs\n'
