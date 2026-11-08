import argparse
import json
import os
from pathlib import Path
from .adapters import HTTPModel, TransformersModel, SystemOneModel
from .data import load_rows, write_json
from .providers import (PROVIDERS, ProviderError, api_base, check_model, describe_catalog,
                        discover_models, model_selector_options,
                        resolve_api_key, resolve_provider)
from .runner import run
from .scoring import score


def provider_list():
    rows = []
    for provider in PROVIDERS.values():
        api_key = next((name for name in provider.key_envs if os.getenv(name)), None)
        rows.append({'id': provider.id, 'label': provider.label, 'base_url': provider.base_url,
                     'catalog_url': provider.catalog_url, 'default_model': provider.default_model,
                     'key_env': provider.key_envs[0], 'key_present': bool(api_key),
                     'docs_url': provider.docs_url, 'description': provider.description})
    print(json.dumps(rows, indent=2))


def provider_models(args):
    provider = resolve_provider(args.provider)
    try:
        api_key = resolve_api_key(provider)
        notice = None
    except ProviderError as e:
        api_key, notice = '', str(e)
    catalog = discover_models(provider, api_key, args.capability)
    payload = describe_catalog(catalog)
    payload['provider'] = provider.id
    payload['capability'] = args.capability
    payload['options'] = model_selector_options(provider, catalog.models, args.capability)
    if notice:
        payload['credential'] = notice
    print(json.dumps(payload, indent=2))
    if catalog.source != 'live':
        return 2
    return 0


def main():
    parser = argparse.ArgumentParser(description='OpenGuardrailsBench: reproducible guardrail evaluation')
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('validate')
    check.add_argument('--rows', required=True)
    scoring = sub.add_parser('score')
    scoring.add_argument('--rows', required=True)
    scoring.add_argument('--results', required=True)
    scoring.add_argument('--out', required=True)
    plist = sub.add_parser('provider', help='inspect named model providers')
    plist_sub = plist.add_subparsers(dest='provider_command', required=True)
    plist_sub.add_parser('list')
    pmodels = plist_sub.add_parser('models', help='discover capability-filtered models')
    pmodels.add_argument('--provider', default='orcarouter')
    pmodels.add_argument('--capability', choices=['text', 'multimodal'], default='text')
    r = sub.add_parser('run')
    r.add_argument('--rows', required=True)
    r.add_argument('--out', required=True)
    r.add_argument('--engine', choices=['http','systemone','transformers','allow-all','block-all'], required=True)
    r.add_argument('--provider', choices=sorted(PROVIDERS), default=None,
                   help='named provider for the http engine (OrcaRouter Cyber Inference)')
    r.add_argument('--model', default=None,
                   help='model id; defaults to the provider default when --provider is set')
    r.add_argument('--adapter', choices=['json','nemotron','nemoguard','qwen_guard','llama_guard','openguardrails_text'], default='json')
    r.add_argument('--base-url', default=None,
                   help='OpenAI-compatible base URL; defaults to the provider base')
    r.add_argument('--revision', default='main')
    r.add_argument('--device', default='cpu')
    r.add_argument('--quantize', action='store_true')
    r.add_argument('--workers', type=int, default=1)
    r.add_argument('--max-tokens', type=int, default=None,
                   help='completion cap for the http engine (defaults to 256; reasoning routes need more)')
    args = parser.parse_args()
    for name, default in (('provider', None), ('model', None), ('base_url', None), ('max_tokens', None)):
        if not hasattr(args, name):
            setattr(args, name, default)
    if args.command == 'provider':
        return provider_list() if args.provider_command == 'list' else provider_models(args)
    explicit_model = getattr(args, 'model', None) is not None
    explicit_base = getattr(args, 'base_url', None) is not None
    if args.provider and args.engine != 'http':
        parser.error('--provider applies to --engine http only')
    rows = load_rows(args.rows)
    if args.command == 'validate':
        print(json.dumps({'valid':True,'rows':len(rows)})); return
    if args.command == 'score':
        results = [json.loads(l) for l in Path(args.results).read_text().splitlines() if l.strip()]
        write_json(args.out, score(rows, results)); return
    if not explicit_model:
        args.model = 'baseline'
    if args.base_url is None:
        args.base_url = 'http://127.0.0.1:8000/v1'
    config = {k:v for k,v in vars(args).items() if k not in {'out','rows','command','provider_command'}}
    http_kwargs = {} if args.max_tokens is None else {'max_tokens': args.max_tokens}
    if args.provider:
        provider = resolve_provider(args.provider)
        api_key = resolve_api_key(provider)
        catalog = discover_models(provider, api_key, 'text')
        if not explicit_model:
            args.model = provider.default_model
        model_filter = catalog.models
        args.model = check_model(provider, args.model, catalog.models, 'text')
        if not explicit_base:
            args.base_url = api_base(provider)
        config.update(provider=provider.id, provider_label=provider.label,
                      model_catalog=describe_catalog(catalog),
                      model_capability='text')
        detector = HTTPModel(args.base_url, args.model, args.adapter, api_key,
                             model_filter=lambda model: check_model(provider, model, model_filter, 'text'),
                             **http_kwargs)
        config['model'] = args.model
        config['base_url'] = args.base_url
    if args.engine == 'http' and not args.provider:
        detector = HTTPModel(args.base_url, args.model, args.adapter, os.getenv('OGB_API_KEY',''),
                             **http_kwargs)
    if args.engine == 'systemone':
        config['threshold'] = 0.5
        config['adapter'] = 'systemone-noul'
        detector = SystemOneModel(args.base_url, args.model, os.getenv('OGB_API_KEY',''))
    if args.engine == 'transformers':
        if args.workers != 1: parser.error('Transformers engine requires --workers 1')
        if args.revision == 'main': parser.error('Pin --revision to a model commit SHA')
        detector = TransformersModel(args.model, args.adapter, args.revision, args.device, args.quantize)
    if args.engine in {'allow-all', 'block-all'}:
        detector = lambda row: {'unsafe': args.engine == 'block-all', 'raw': args.engine}
    print(json.dumps(run(rows, detector, args.out, config, args.workers), indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
