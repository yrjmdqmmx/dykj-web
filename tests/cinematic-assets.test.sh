#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TEST_FILES=(
  "$SCRIPT_DIR/cinematic_assets_test.py"
  "$SCRIPT_DIR/cinematic_package_runtime_test.py"
)

if python3 -c 'from PIL import Image' >/dev/null 2>&1; then
  for test_file in "${TEST_FILES[@]}"; do
    python3 "$test_file"
  done
  exit 0
fi

if command -v uv >/dev/null 2>&1; then
  for test_file in "${TEST_FILES[@]}"; do
    uv run --quiet --with 'Pillow==12.2.0' python "$test_file"
  done
  exit 0
fi

printf '%s\n' 'cinematic-assets: Pillow is required (install source/blender/requirements-preview.txt)' >&2
exit 1
