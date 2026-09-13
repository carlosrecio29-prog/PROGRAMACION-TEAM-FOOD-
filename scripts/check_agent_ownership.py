"""Minimal ownership checker with no PyYAML dependency."""
from __future__ import annotations
import fnmatch, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def changed():
    p = subprocess.run(['git','diff','--name-only','HEAD'], cwd=ROOT, text=True, capture_output=True, check=False)
    files = set(p.stdout.splitlines())
    p = subprocess.run(['git','ls-files','--others','--exclude-standard'], cwd=ROOT, text=True, capture_output=True, check=False)
    return {x.replace('\\','/') for x in files | set(p.stdout.splitlines()) if x}
def ownership():
    result, role = {}, None
    for line in open(os.path.join(ROOT,'.ai','ownership.yaml'), encoding='utf-8'):
        s=line.strip()
        if s.endswith(':') and not s.startswith('-') and s[:-1] in {'database','backend','frontend','qa','security-release','lead','shared'}: role=s[:-1]; result[role]=[]
        elif role and s.startswith('- '): result[role].append(s[2:].strip())
    return result
def main():
    role=os.getenv('AGENT_ROLE') or (sys.argv[1] if len(sys.argv)>1 else '')
    files=changed(); rules=ownership()
    if not files: print('OWNERSHIP CHECK: no changed files'); return 0
    if role in ('lead','shared'):
        print(f'OWNERSHIP CHECK: {role} override for {len(files)} file(s)'); return 0
    if role not in rules: print('Set AGENT_ROLE to one of: '+', '.join(rules)); return 2
    foreign=[f for f in files if not any(fnmatch.fnmatch(f,p) for p in rules[role]+rules.get('shared',[]))]
    if foreign:
        print(f'OWNERSHIP BLOCKED for {role}:'); print('\n'.join(f'  {f}' for f in sorted(foreign))); return 1
    print(f'OWNERSHIP CHECK: {role} owns all {len(files)} changed file(s)'); return 0
if __name__ == '__main__': sys.exit(main())
