#!/bin/bash
set -euo pipefail
app_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build_python="${CODETOP_BUILD_PYTHON:-$app_root/backend/.venv/bin/python}"
if [[ ! -x "$build_python" ]]; then
  printf '%s\n' 'Create the Python 3.12.13 build environment first; see docs/deployment.md.' >&2
  exit 1
fi
exec "$build_python" "$app_root/scripts/build_macos.py" "$@"
