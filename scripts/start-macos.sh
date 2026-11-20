#!/bin/bash
set -euo pipefail
app_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_exe="$app_root/backend/.venv/bin/python"
if [[ ! -x "$python_exe" || ! -f "$app_root/releases/current.json" ]]; then
  printf '%s\n' 'Prepare the backend environment and frontend release first; see docs/deployment.md.' >&2
  exit 1
fi
cd -- "$app_root/backend"
export CODETOP_RUNNER=native
if [[ "${1:-}" == '--no-browser' ]]; then
  shift
  exec "$python_exe" -m app.serve "$@"
fi
exec "$python_exe" -m app.desktop "$@"
