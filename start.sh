#!/usr/bin/env bash
set -e
export PYTHONPATH="${PYTHONPATH:-$PWD/public}:$PWD/public"
cd workflow/backend && exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
