"""Safety signal for changed files; never scans the whole historical repository."""
from __future__ import annotations
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def run(*args: str) -> list[str]:
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    return [x.replace('\\', '/') for x in p.stdout.splitlines() if x.strip()]

def main() -> int:
    files = set(run('git', 'diff', '--name-only', 'HEAD')) | set(run('git', 'ls-files', '--others', '--exclude-standard'))
    raw_diff = subprocess.run(['git', 'diff', '--unified=0', 'HEAD', '--', *sorted(files)], cwd=ROOT, text=True, capture_output=True, check=False).stdout if files else ''
    # Removed lines are evidence of a safer change, not newly executable risk.
    diff = '\n'.join(line for line in raw_diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
    findings: list[tuple[str, str]] = []
    for path in sorted(files):
        if re.search(r'(?:^|/)(?:migrations|migrations_v2)/', path) and path in run('git', 'diff', '--name-only', '--diff-filter=M', 'HEAD'):
            findings.append(('BLOCKING', f'Applied/committed migration modified: {path}'))
    patterns = [
        (r'\bTRUNCATE\b', 'TRUNCATE'), (r'\bDROP\s+(?:TABLE|COLUMN|SCHEMA)\b', 'DROP'),
        (r'\bCASCADE\b', 'CASCADE'), (r'\bDELETE\s+FROM\s+[\w.]+\s*(?:;|$)', 'unfiltered DELETE'),
    ]
    for pat, label in patterns:
        if re.search(pat, diff, re.I): findings.append(('REVIEW REQUIRED', f'{label} in changed diff'))
    if re.search(r'\b(?:TRUNCATE|DROP|DELETE\s+FROM|REPLACE\s+INTO)\b', diff, re.I):
        findings.append(('REVIEW REQUIRED', 'Potential broad data replacement; inspect transaction and predicates'))
    for level, msg in findings: print(f'{level}: {msg}')
    if not findings:
        print('DESTRUCTIVE CHECK: no dangerous patterns in current diff')
        return 0
    if os.getenv('DESTRUCTIVE_CHANGE_APPROVED') == '1':
        print('Override present; evidence and approval must exist in the PR.')
        return 0
    return 1 if any(level == 'BLOCKING' for level, _ in findings) else 2

if __name__ == '__main__': sys.exit(main())
