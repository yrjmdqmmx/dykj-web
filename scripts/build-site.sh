#!/usr/bin/env bash

set -euo pipefail

fail() {
  printf 'build-site: %s\n' "$*" >&2
  exit 1
}

[ "$#" -eq 1 ] || fail "usage: scripts/build-site.sh OUTPUT_DIR"
[ -n "$1" ] || fail "OUTPUT_DIR must not be empty"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
EXPECTED_OUTPUT_DIR="$REPO_ROOT/_site"
OUTPUT_ARG="$1"

[ ! -L "$OUTPUT_ARG" ] || fail "OUTPUT_DIR must not be a symbolic link"

if [ -e "$OUTPUT_ARG" ]; then
  [ -d "$OUTPUT_ARG" ] || fail "OUTPUT_DIR exists and is not a directory"
  OUTPUT_DIR="$(cd "$OUTPUT_ARG" && pwd -P)"
else
  OUTPUT_PARENT="$(dirname "$OUTPUT_ARG")"
  [ -d "$OUTPUT_PARENT" ] || fail "OUTPUT_DIR parent does not exist"
  OUTPUT_PARENT="$(cd "$OUTPUT_PARENT" && pwd -P)"
  OUTPUT_DIR="$OUTPUT_PARENT/$(basename "$OUTPUT_ARG")"
fi

[ "$OUTPUT_DIR" != "/" ] || fail "refusing to build into filesystem root"
[ "$OUTPUT_DIR" != "$REPO_ROOT" ] || fail "refusing to build into repository root"
[ "$OUTPUT_DIR" = "$EXPECTED_OUTPUT_DIR" ] || fail "OUTPUT_DIR must resolve to $EXPECTED_OUTPUT_DIR"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

for directory in css js assets; do
  cp -R "$REPO_ROOT/$directory" "$OUTPUT_DIR/$directory"
done

# Legacy pump walkthrough assets remain in source history for reference but are
# no longer part of the public site after the v2 company scrollytelling launch.
rm -rf "$OUTPUT_DIR/assets/pump-seq"
rm -f "$OUTPUT_DIR/js/pump-scrolly.js"

shopt -s nullglob
html_files=("$REPO_ROOT"/*.html)
[ "${#html_files[@]}" -gt 0 ] || fail "no root HTML files found"
cp "${html_files[@]}" "$OUTPUT_DIR/"

for file in favicon.ico robots.txt sitemap.xml .nojekyll; do
  if [ -e "$REPO_ROOT/$file" ]; then
    cp "$REPO_ROOT/$file" "$OUTPUT_DIR/$file"
  fi
done

printf 'Built static site: %s\n' "$OUTPUT_DIR"
