#!/usr/bin/env python3
"""Blind author-model consistency audit; does NOT create independent ground truth."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ogb.adapters import HTTPModel
from ogb.data import load_rows, write_json
from ogb.runner import run

p=argparse.ArgumentParser();p.add_argument('--rows',required=True);p.add_argument('--out',default='work/author-consistency');p.add_argument('--base-url',default='http://127.0.0.1:56690/v1');a=p.parse_args()
rows=load_rows(a.rows)
detector=HTTPModel(a.base_url,'qwen3.8-27b',max_tokens=256)
run(rows,detector,a.out,{'engine':'http','model':'qwen3.8-27b','role':'author-model-consistency-ineligible-for-ranking','adapter':'json','max_tokens':256},workers=4)
ps={r['id']:r for r in [json.loads(l) for l in (Path(a.out)/'results.jsonl').read_text().splitlines()]}
flagged=[{'id':r['id'],'expected':r['unsafe'],'prediction':ps.get(r['id'],{}).get('unsafe'),'status':ps.get(r['id'],{}).get('status')} for r in rows if ps.get(r['id'],{}).get('unsafe')!=r['unsafe']]
write_json(Path(a.out)/'disagreements.json',flagged)
print('Flagged for adjudication:',len(flagged))
