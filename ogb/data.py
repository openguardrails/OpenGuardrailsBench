"""Strict suite validation and stable content fingerprints."""
import hashlib
import json
from pathlib import Path

SPLITS = {"public", "private_same", "private_novel"}

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()

def model_input(row):
    return {k: row[k] for k in ("policy", "context", "text", "target")}

def load_rows(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    validate(rows)
    return rows

def validate(rows):
    ids, fingerprints = set(), set()
    for r in rows:
        for k in ("id", "pair_id", "split", "area", "skill", "domain", "language",
                  "policy", "context", "text", "target", "unsafe", "rationale", "provenance"):
            if k not in r:
                raise ValueError(f"Missing {k}: {r.get('id')}")
        if r["id"] in ids or digest(model_input(r)) in fingerprints:
            raise ValueError(f"Duplicate case/input: {r['id']}")
        if r["split"] not in SPLITS or type(r["unsafe"]) is not bool:
            raise ValueError(f"Invalid split/label: {r['id']}")
        if r["target"] not in {"user", "assistant", "action", "untrusted_content"}:
            raise ValueError(f"Invalid target: {r['id']}")
        if not all(isinstance(r[k], str) and r[k].strip() for k in
                   ("policy", "text", "rationale", "skill", "area", "context")):
            raise ValueError(f"Empty/non-string input: {r['id']}")
        ids.add(r["id"])
        fingerprints.add(digest(model_input(r)))
    return rows

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")

def write_rows(path, rows):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
