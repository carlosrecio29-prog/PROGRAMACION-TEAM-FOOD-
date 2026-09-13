#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
echo '== Harness: Python compile =='; "$PYTHON_BIN" -m py_compile scripts/check_destructive_changes.py scripts/check_agent_ownership.py
echo '== Destructive-change guard =='; "$PYTHON_BIN" scripts/check_destructive_changes.py
echo '== Backend =='; bash scripts/verify_backend.sh
echo '== Frontend =='; bash scripts/verify_frontend.sh
echo '== Database =='; bash scripts/verify_database.sh
echo 'VERIFICATION: all configured gates passed'
