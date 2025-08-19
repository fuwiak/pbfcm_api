#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-8000}"
APP_MODULE="${APP_MODULE:-pbfcm_api:app}"
exec uvicorn "$APP_MODULE" --host 0.0.0.0 --port "$PORT" --workers 1 --log-level warning
