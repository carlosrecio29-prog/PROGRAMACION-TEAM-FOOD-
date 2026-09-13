#!/usr/bin/env bash
set -euo pipefail
if command -v node.exe >/dev/null 2>&1 && command -v cmd.exe >/dev/null 2>&1; then NPM_PREFIX=(cmd.exe /c npm); else NPM_PREFIX=(npm); fi
if [ -f package-lock.json ]; then "${NPM_PREFIX[@]}" ci --ignore-scripts; else echo 'WARNING: package-lock.json absent; using npm install (non-reproducible).'; "${NPM_PREFIX[@]}" install --ignore-scripts --no-audit --no-fund; fi
"${NPM_PREFIX[@]}" run build
if "${NPM_PREFIX[@]}" run | grep -qE '^  test'; then "${NPM_PREFIX[@]}" test -- --run; fi
