#!/usr/bin/env python3
"""Reuse unchanged case predictions after an explicitly documented pilot correction."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ogb.data import digest,model_input,load_rows,write_rows,write_json
p=argparse.ArgumentParser();p.add_argument('--rows',required=True);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args()
rows={r['id']:r for r in load_rows(a.rows)}
for source in Path(a.source).glob('*/config.json'):
    d=source.parent
    if not (d/'scores.json').exists():continue
    cfg=json.loads(source.read_text())
    ps=[json.loads(l) for l in (d/'results.jsonl').read_text().splitlines() if l.strip()]
    retained=[r for r in ps if r['id'] in rows and r.get('status')=='ok' and r.get('input_hash')==digest(model_input(rows[r['id']]))]
    out=Path(a.out)/d.name
    if (out/'config.json').exists():raise ValueError('Refusing to overwrite an active run')
    write_rows(out/'results.jsonl',retained)
    write_json(out/'checkpoint_origin.json',{'source_config':cfg,'retained_unchanged_cases':len(retained),
                'new_suite_hash':digest(list(rows.values())), 'reason':'Blind author consistency audit and editorial policy clarification; no guard-model outputs used to select corrections.'})
    print(d.name,len(retained),'retained; remaining',len(rows)-len(retained))
