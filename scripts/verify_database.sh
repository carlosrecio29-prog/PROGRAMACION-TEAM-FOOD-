#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" scripts/check_destructive_changes.py || test "$?" -eq 2
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
files=sorted(Path('supabase/migrations_v2').glob('*.sql'))
names=[p.name.split('_',1)[0] for p in files]
assert len(names)==len(set(names)), 'duplicate V2 migration timestamps'
assert files, 'no V2 migrations found'
print(f'DATABASE CHECK: {len(files)} ordered V2 migrations; production credentials not required')
PY
