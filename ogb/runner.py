import json
import hashlib
from importlib import metadata
import platform
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .data import digest, model_input, write_json
from .scoring import score


def run(rows, detector, out, config, workers=1):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    identity = {**config, 'suite_hash': digest(rows), 'version': '0.1.0'}
    config_path = out / 'config.json'
    if config_path.exists() and json.loads(config_path.read_text()) != identity:
        raise ValueError('Resume rejected: model/config/suite changed; choose a fresh output directory')
    write_json(config_path, identity)
    env = {'python': platform.python_version(), 'platform': platform.platform(),
           'workers': workers, 'warmup_requests': 0,
           'model_revision': getattr(detector, 'revision', config.get('revision'))}
    env['packages'] = {}
    for package in ['torch', 'transformers', 'huggingface_hub', 'bitsandbytes', 'accelerate']:
        try: env['packages'][package] = metadata.version(package)
        except metadata.PackageNotFoundError: pass
    tokenizer = getattr(detector, 'tokenizer', None)
    if tokenizer is not None:
        env['chat_template_sha256'] = hashlib.sha256(str(tokenizer.chat_template).encode()).hexdigest()
    torch = getattr(detector, 'torch', None)
    if torch is not None and torch.cuda.is_available():
        env['gpu'] = torch.cuda.get_device_name(0)
        env['cuda_runtime'] = torch.version.cuda
    write_json(out / 'environment.json', env)
    result_path = out / 'results.jsonl'
    existing = {}
    if result_path.exists():
        for line in result_path.read_text().splitlines():
            p = json.loads(line)
            if p['id'] in existing: raise ValueError('Duplicate checkpoint id')
            existing[p['id']] = p
    wanted = {r['id']: r for r in rows}
    if set(existing) - set(wanted): raise ValueError('Checkpoint contains unknown ids')
    for key, value in existing.items():
        if value['input_hash'] != digest(model_input(wanted[key])):
            raise ValueError('Checkpoint input changed')
    todo = [r for r in rows if existing.get(r['id'], {}).get('status') != 'ok']
    def evaluate(row):
        t = time.perf_counter()
        result = {'id': row['id'], 'input_hash': digest(model_input(row))}
        try:
            prediction = detector(row)
            result.update(prediction)
            result['status'] = 'ok' if type(prediction.get('unsafe')) is bool else 'invalid'
        except Exception as e:
            result.update(status='error', unsafe=None, error=type(e).__name__ + ': ' + str(e)[:500])
        result['latency_ms'] = (time.perf_counter()-t)*1000
        return result
    # Only the owner thread writes checkpoints. Failed rows replace previous attempts.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(evaluate, r) for r in todo]):
            p = future.result()
            existing[p['id']] = p
            temp = out / 'results.jsonl.tmp'
            temp.write_text(''.join(json.dumps(existing[k], ensure_ascii=False)+'\n' for k in sorted(existing)))
            temp.replace(result_path)
            print(f"{len(existing)}/{len(rows)} {p['id']} {p['status']}", flush=True)
    summary = score(rows, list(existing.values()))
    write_json(out / 'scores.json', summary)
    return summary
