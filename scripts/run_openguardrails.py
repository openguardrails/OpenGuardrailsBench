#!/usr/bin/env python3
"""Evaluate the deployed OpenGuardrails model, pinning container and weight metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ogb.adapters import SystemOneModel
from ogb.data import load_rows,write_json
from ogb.runner import run

p=argparse.ArgumentParser()
p.add_argument('--rows',required=True)
p.add_argument('--out',default='work/openguardrails-xiangxin-3.0.7')
p.add_argument('--base-url',default='http://127.0.0.1:18834/v1')
p.add_argument('--container',default='xiangxin3-tp2')
a=p.parse_args()
def identity():
    info=json.loads(subprocess.check_output(['docker','inspect',a.container],text=True))[0]
    return {'container_id':info['Id'],'image_id':info['Image']}
receipt=identity()
info=json.loads(subprocess.check_output(['docker','inspect',a.container],text=True))[0]
weights=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/models'))
receipt['weight_metadata']={}
for name in ['config.json','model.safetensors.index.json','tokenizer_config.json']:
    file=weights/name
    if file.exists():receipt['weight_metadata'][name]=hashlib.sha256(file.read_bytes()).hexdigest()
write_json(Path(a.out)/'deployment.json',receipt)
detector=SystemOneModel(a.base_url,'xiangxin-3.0')
def pinned(row):
    if identity()!={k:receipt[k] for k in ['container_id','image_id']}:
        raise RuntimeError('Deployed container changed; refusing to mix model versions')
    return detector(row)
config={'engine':'systemone','model':'OpenGuardrails/Xiangxin-3.0.7','api_model':'xiangxin-3.0',
        'adapter':'systemone-noul','revision':receipt['image_id'],'deployment':receipt,
        'threshold':0.5,'serialization':'policy-context-target-v1','quantize_nf4':False,
        'precision':'BF16','hardware':'shared t3090, 2 x RTX A6000, tensor parallel 2',
        'scope':'Model backend only; not AIRS rule engine, cache or detector composition.',
        'affiliation':'Maintainer-owned model; self-evaluated; not an independent assessment.'}
run(load_rows(a.rows),pinned,a.out,config,workers=4)
assert identity()=={k:receipt[k] for k in ['container_id','image_id']},'Container changed'
