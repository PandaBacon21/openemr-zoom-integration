#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export UV_CACHE_DIR="${UV_CACHE_DIR:-${SERVER_DIR}/.uv-cache}"
export PYTHONPATH="${SERVER_DIR}:${PYTHONPATH:-}"

cd "${SERVER_DIR}"
exec uv run pytest -q "$@"
