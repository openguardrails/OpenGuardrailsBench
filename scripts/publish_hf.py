#!/usr/bin/env python3
"""Explicit allowlist uploads; no recursive uploads of the repository."""
import argparse
import base64
import json
import os
from pathlib import Path
import urllib.request
import urllib.error


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--org',default='openguardrails')
    p.add_argument('--name',default='OpenGuardrailsBench')
    p.add_argument('--private-dir',default='private')
    p.add_argument('--public-only',action='store_true')
    p.add_argument('--target',choices=['all','data','space'],default='all')
    p.add_argument('--verify',action='store_true',help='Read-only deployment and visibility checks')
    a=p.parse_args()
    token=os.getenv('HF_TOKEN')
    cache=Path.home()/'.cache/huggingface/token'
    if not token and cache.exists():token=cache.read_text().strip()
    if not token:raise SystemExit('HF_TOKEN or a valid Hugging Face login is required')
    def request(path,body=None):
        req=urllib.request.Request('https://huggingface.co'+path,
           data=json.dumps(body).encode() if body is not None else None,
           headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
    if a.verify:
        public=request(f'/api/datasets/{a.org}/{a.name}')
        private=request(f'/api/datasets/{a.org}/{a.name}-private')
        space=request(f'/api/spaces/{a.org}/{a.name}')
        runtime=request(f'/api/spaces/{a.org}/{a.name}/runtime')
        if public.get('private') or not private.get('private') or space.get('private'):
            raise RuntimeError('Release visibility check failed')
        try:
            urllib.request.urlopen(f'https://huggingface.co/api/datasets/{a.org}/{a.name}-private',timeout=30)
            raise RuntimeError('Private dataset is visible anonymously')
        except urllib.error.HTTPError as error:
            if error.code not in [401,403,404]:raise
        host=space.get('host')
        if not host and runtime.get('domains'):
            host=runtime['domains'][0]['domain']
        if host and not host.startswith('http'):host='https://'+host
        receipt={'public_dataset':public['id'],'private_dataset':private['id'],
                 'private_verified':True,'space_stage':runtime.get('stage'),'host':host}
        if host:
            with urllib.request.urlopen(host,timeout=60) as response:
                html=response.read().decode()
            if 'OpenGuardrailsBench' not in html:raise RuntimeError('Hosted app content mismatch')
            with urllib.request.urlopen(host.rstrip('/')+'/leaderboard.json',timeout=60) as response:
                board=json.load(response)
            receipt['hosted_models']=len(board['models'])
            receipt['public_cases']=board['models'][0]['parts']['public']['n'] if board['models'] else 0
        print(json.dumps(receipt),flush=True)
        return
    def ensure(kind,name,private=False):
        try:request('/api/repos/create',{'type':kind,'name':name,'organization':a.org,
             'private':private,**({'sdk':'static'} if kind=='space' else {})})
        except urllib.error.HTTPError as e:
            if e.code!=409:raise
        info=request(f'/api/{kind}s/{a.org}/{name}')
        if bool(info.get('private'))!=private:raise RuntimeError('Repo visibility mismatch; refusing upload')
        return f'{a.org}/{name}'
    def upload(kind,repo,files):
        ops=[{'key':'header','value':{'summary':'Publish OpenGuardrailsBench pilot artifacts'}}]
        for target,source in files.items():
            raw=Path(source).read_bytes()
            ops.append({'key':'file','value':{'path':target,'encoding':'base64',
                       'content':base64.b64encode(raw).decode()}})
        req=urllib.request.Request(f'https://huggingface.co/api/{kind}s/{repo}/commit/main',
          data=('\n'.join(json.dumps(op) for op in ops)+'\n').encode(),
          headers={'Authorization':'Bearer '+token,'Content-Type':'application/x-ndjson'})
        try:
            with urllib.request.urlopen(req,timeout=180) as r:receipt=json.load(r)
        except urllib.error.HTTPError as error:
            print(error.read().decode()[:2000],flush=True)
            raise
        print(json.dumps({'repo':repo,'type':kind,'commit':receipt.get('commitOid')}),flush=True)
    if a.target != 'space':
        pub=ensure('dataset',a.name)
        upload('dataset',pub,{'README.md':'data/README.md','public/ogb-0.1.jsonl':'data/public/ogb-0.1.jsonl',
                              'manifest.json':'data/manifest.json', 'author-deployment.json':'data/author-deployment.json'})
        if not a.public_only:
            private=ensure('dataset',a.name+'-private',True)
            directory=Path(a.private_dir)
            files={n:str(directory/n) for n in ['all.jsonl','private_same.jsonl','private_novel.jsonl','tracks.json','corrections.json','manifest.json']}
            files['README.md']='private/README.md'
            for run in Path('work/runs-final').iterdir():
                if not run.is_dir():continue
                for filename in ['config.json','environment.json','results.jsonl','scores.json','checkpoint_origin.json']:
                    source=run/filename
                    if source.exists():files[f'runs/{run.name}/{filename}']=str(source)
            for label,source in [('initial-disagreements','work/batch-review/disagreements.json'),('editorial-followup','work/editorial-followup/disagreements.json')]:
                if Path(source).exists():files[f'audit/{label}.json']=source
            upload('dataset',private,files)
    if a.target != 'data':
        space=ensure('space',a.name)
        upload('space',space,{'README.md':'space/README.md','index.html':'space/index.html',
                              'leaderboard.json':'results/leaderboard.json', 'methodology.md':'docs/methodology.md'})
        print('https://huggingface.co/spaces/'+space)

if __name__=='__main__':main()
