"""Reject held-out cases and outputs from the public release surface."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ogb.data import load_rows

rows=load_rows('data/public/ogb-0.1.jsonl')
public_ids={r['id'] for r in rows}
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],text=True).splitlines()
for name in files:
    if name.startswith(('private/','work/')):raise SystemExit(f'Private path tracked: {name}')
    if name.startswith('legacy/') or not Path(name).exists():continue
    if name.endswith('.jsonl'):
        for line in Path(name).read_text().splitlines():
            row=json.loads(line)
            if row.get('split','public')!='public' or row.get('id') not in public_ids:raise SystemExit(f'Held-out row in public release: {name}')
rows=load_rows('data/public/ogb-0.1.jsonl')
assert {r['split'] for r in rows}=={'public'}
print(f'Release check passed: {len(rows)} public rows; no held-out rows in release surface')

manifest=json.loads(Path('data/manifest.json').read_text())
actual=hashlib.sha256(Path('data/public/ogb-0.1.jsonl').read_bytes()).hexdigest()
if actual!=manifest['partitions']['public']['sha256']:raise SystemExit('Public suite changed without a matching frozen manifest')
