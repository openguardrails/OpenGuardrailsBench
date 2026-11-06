---
license: apache-2.0
language:
- en
- zh
task_categories:
- text-classification
tags:
- guardrails
- safety
- security
- privacy
- synthetic
pretty_name: OpenGuardrailsBench
configs:
- config_name: public-pilot
  data_files:
  - split: test
    path: public/ogb-0.1.jsonl
---
# OpenGuardrailsBench (OGB): public pilot

192 original synthetic guardrail classification cases: 12 skills, 8 safe/unsafe minimal pairs per skill. Initial cases and labels were authored with a Qwen service on t3090. These are provisional machine labels, with independent human adjudication pending.

Fields: `id`, `pair_id`, `split`, `area`, `skill`, `domain`, `language`, `policy`, `context`, `text`, `target`, `unsafe`, `rationale`, `provenance`. Judge only `text` as the specified `target`, in the supplied `context` under `policy`. `unsafe=true` means a policy violation.

Public cases support reproducibility and submission validation. They carry zero Full-index weight. Maintainers evaluate a separate private same-skill set (60%) and private novel set (40%). `manifest.json` commits to frozen file hashes without revealing held-out contents. Full pilot results are provisional and are not calibrated to Jev's scale.

All records, credentials and entities are fictional. This dataset is for guardrail evaluation and contains short examples of unsafe intent and quoted harmful language. No third-party benchmark sources are redistributed. Original synthetic cases are released under Apache-2.0; model licenses are separate.

Code: https://github.com/openguardrails/OpenGuardrailsBench
Leaderboard: https://huggingface.co/spaces/openguardrails/OpenGuardrailsBench
Inspired by Decision Index, with independently authored tasks and its own scoring.
