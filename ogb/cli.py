import argparse
import json
import os
from pathlib import Path
from .adapters import HTTPModel, TransformersModel
from .data import load_rows, write_json
from .runner import run
from .scoring import score


def main():
    parser = argparse.ArgumentParser(description='OpenGuardrailsBench: reproducible guardrail evaluation')
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('validate')
    check.add_argument('--rows', required=True)
    scoring = sub.add_parser('score')
    scoring.add_argument('--rows', required=True)
    scoring.add_argument('--results', required=True)
    scoring.add_argument('--out', required=True)
    r = sub.add_parser('run')
    r.add_argument('--rows', required=True)
    r.add_argument('--out', required=True)
    r.add_argument('--engine', choices=['http','transformers','allow-all','block-all'], required=True)
    r.add_argument('--model', default='baseline')
    r.add_argument('--adapter', choices=['json','nemotron','nemoguard','qwen_guard','llama_guard'], default='json')
    r.add_argument('--base-url', default='http://127.0.0.1:8000/v1')
    r.add_argument('--revision', default='main')
    r.add_argument('--device', default='cpu')
    r.add_argument('--quantize', action='store_true')
    r.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    rows = load_rows(args.rows)
    if args.command == 'validate':
        print(json.dumps({'valid':True,'rows':len(rows)})); return
    if args.command == 'score':
        results = [json.loads(l) for l in Path(args.results).read_text().splitlines() if l.strip()]
        write_json(args.out, score(rows, results)); return
    config = {k:v for k,v in vars(args).items() if k not in {'out','rows','command'}}
    if args.engine == 'http':
        detector = HTTPModel(args.base_url, args.model, args.adapter, os.getenv('OGB_API_KEY',''))
    elif args.engine == 'transformers':
        if args.workers != 1: parser.error('Transformers engine requires --workers 1')
        if args.revision == 'main': parser.error('Pin --revision to a model commit SHA')
        detector = TransformersModel(args.model, args.adapter, args.revision, args.device, args.quantize)
    else:
        detector = lambda row: {'unsafe': args.engine == 'block-all', 'raw': args.engine}
    print(json.dumps(run(rows, detector, args.out, config, args.workers), indent=2))
