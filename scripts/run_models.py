#!/usr/bin/env python3
"""Download pinned open-weight baselines and evaluate sequentially on a shared GPU."""
import argparse
import gc
import json
from pathlib import Path
import sys
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ogb.adapters import TransformersModel
from ogb.data import load_rows, write_json
from ogb.runner import run

MODELS = [
 ('qwen3guard-0.6b','Qwen/Qwen3Guard-Gen-0.6B','qwen_guard',False),
 ('nemotron-safety-4b','nvidia/Nemotron-Content-Safety-Reasoning-4B','nemotron',True),
 ('nemotron-safety-8b-v3','nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3','nemoguard',True),
 ('qwen3guard-4b','Qwen/Qwen3Guard-Gen-4B','qwen_guard',True),
 ('llama-guard-3-1b','meta-llama/Llama-Guard-3-1B','llama_guard',False),
]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rows',required=True)
    p.add_argument('--out',default='work/runs')
    p.add_argument('--device',default='cuda:0')
    p.add_argument('--only',nargs='*')
    p.add_argument('--offload-embeddings',action='store_true')
    a=p.parse_args()
    from huggingface_hub import HfApi
    import torch
    torch.cuda.set_per_process_memory_fraction(.32, 0)
    rows=load_rows(a.rows)
    for slug,model,adapter,quant in MODELS:
        if a.only and slug not in a.only:continue
        out=Path(a.out)/slug
        out.mkdir(parents=True,exist_ok=True)
        try:
            revision=HfApi().model_info(model).sha
            write_json(out/'attempt.json',{'model':model,'revision':revision,'adapter':adapter,'quantize_nf4':quant})
            print('loading',slug,revision,flush=True)
            detector=TransformersModel(model,adapter,revision,a.device,quant,a.offload_embeddings)
            cfg={'engine':'transformers','model':model,'adapter':adapter,'revision':revision,
                 'device':a.device,'offload_embeddings':a.offload_embeddings,'quantize_nf4':quant,'max_new_tokens':128,'temperature':0,
                 'serialization':'policy-context-target-v1','hardware':'shared RTX 4090; 32% process allocator cap'}
            if model.startswith('openguardrails/'):
                cfg['affiliation']='Maintainer-owned open-weight model; self-evaluated; not an independent assessment.'
                cfg['scope']='Published policy/context text wrapper with native safe/unsafe output parsing.'
            run(rows,detector,out,cfg)
            del detector
        except Exception as e:
            traceback.print_exc()
            write_json(out/'failure.json',{'model':model,'error':type(e).__name__+': '+str(e)[:1500]})
        gc.collect()
        torch.cuda.empty_cache()

if __name__=='__main__':main()
