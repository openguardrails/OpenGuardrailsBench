<div align="center">

# OpenGuardrailsBench (OGB)

**A reproducible benchmark for AI guardrails: safety, security, privacy, and policy.**

[Methodology](docs/methodology.md) · [Public suite](data/public/) · [Results](results/RESULTS.md) · [Run a model](#run-a-model)

Apache-2.0 · maintained by OpenGuardrails

</div>

OpenGuardrailsBench tests whether a guardrail can distinguish a policy violation from a legitimate request in context. It includes hard negatives, paired counterexamples, Chinese and English inputs, explicit authorization, and evidence-dependent decisions.

**Edition 0.1 is a synthetic pilot.** Cases and initial labels are authored by the existing Qwen service on t3090. Structural checks and model review do not replace independent human adjudication. Pilot scores describe this frozen suite; they are not production safety guarantees. No historical protocol benchmark numbers are reused.

| Partition | Purpose | Access | Full score weight |
|---|---|---|---:|
| Public | Reproduce the evaluation and validate submissions | Open cases and labels | 0% |
| Private same skills | Unseen scenarios for the public skills | Maintainer-only dataset | 60% |
| Private novel | New policy skills in additional domains | Maintainer-only dataset | 40% |

A complete public run is required for a Full score. Public-only runs display a Public index and leave Full blank. The index uses chance-corrected balanced accuracy, with equal area weights and equal skill weights within each area. Always-allow and always-block both score zero. Missing and malformed predictions count as wrong. See [the exact scoring contract](docs/methodology.md).

The structure is inspired by [Decision Index](https://github.com/apolinario/decision-index) and its [Jev leaderboard](https://huggingface.co/spaces/multimodalart/jev-decision-index). OpenGuardrailsBench has its own tasks and scoring; it does not reproduce or claim equivalence to Jev scores.

| Area | Pilot skills |
|---|---|
| Content safety | Violence/weapons, hate/harassment, self-harm, sexual safety |
| Security | Prompt injection, unauthorized commands, data exfiltration |
| Privacy | Personal information, secret disclosure |
| Trust & policy | Grounding, medical boundaries, topic/authorization |
| Held-out new domains | Unpublished cases and policy skills; aggregate results only |

## Run a model

The HTTP runner and scorers use only the Python standard library:

```bash
python -m pip install -e .
python -m ogb validate --rows data/public/ogb-0.1.jsonl
python -m ogb run --engine http --adapter json \
  --model YOUR_MODEL --base-url http://localhost:8000/v1 \
  --rows data/public/ogb-0.1.jsonl --out work/my-model-public
```

API keys come from `OGB_API_KEY`. Pin the server model revision in your deployment and keep its receipt with the submission. Resume with the identical command: successful rows are retained, errors and invalid outputs are retried. Changing the model, suite, or configuration requires a new output directory.

For a local open-weight model:

```bash
python -m pip install -e '.[models]'
python -m ogb run --engine transformers --adapter qwen_guard \
  --model Qwen/Qwen3Guard-Gen-0.6B --revision MODEL_COMMIT_SHA \
  --device cuda:0 --rows data/public/ogb-0.1.jsonl \
  --out work/qwen-guard-public
```

Adapters: JSON classifiers, Qwen3Guard, NVIDIA NemoGuard, NVIDIA Nemotron Safety Reasoning, and Llama Guard. Some models need gated base weights; access failures are recorded, never replaced with invented scores. Four-bit runs must be labeled as such. Each model's license applies separately.

**Protocol scope:** the pilot serializes policy, evidence and target into text for native fixed-taxonomy guards. This measures contextual policy classification under that wrapper, not the vendor's original native content benchmark. Models that cannot follow custom policies may perform poorly on policy tracks. We report per-area breakdowns and the exact adapter.

## Inspect results

The first five open-weight model runs are complete: [measured pilot results](results/RESULTS.md). Nemotron Safety Reasoning 4B (NF4) has a provisional Full index of 67.55; Qwen3Guard 4B (NF4) has 50.31. One truncated NVIDIA 8B response leaves its Full index blank. These scores measure the published policy/context wrapper, not native vendor benchmark performance.

Each run saves `config.json`, `environment.json`, `results.jsonl`, and `scores.json`. Raw public predictions may be published. Private prompts, case identifiers, rationales, and model outputs stay private; the public leaderboard gets aggregate counts and scores only.

```bash
python -m ogb score --rows data/public/ogb-0.1.jsonl \
  --results work/my-model-public/results.jsonl --out work/my-model-public/scores.json
python -m pytest -q
python scripts/check_release.py
```

## Maintainers

[Authoring and release](docs/maintainers.md) covers t3090 Qwen generation, independent review, public/private leakage checks, open-model runs, and Hugging Face deployment. `scripts/publish_hf.py` uses an explicit allowlist: the public dataset and leaderboard Space cannot upload held-out files.

The previous protocol and integration monorepo is preserved under [`legacy/`](legacy/). Its archived examples, governance, CI and numbers are outside OpenGuardrailsBench's package and evaluation. Git history remains intact.

Code and original synthetic public cases: Apache-2.0. Model weights and upstream datasets retain their own terms. No third-party benchmark data is bundled in this pilot.
