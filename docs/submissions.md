# OGB model submissions

Provide the exact model repository and commit, public prediction JSONL, complete `config.json` and `environment.json`, model license, tokenizer/chat-template version, parameter precision/quantization, and any fine-tuning or benchmark exposure disclosures.

The public suite must be complete. Maintainers verify IDs and input hashes, rerun the public suite with the same adapter, and run held-out partitions privately. A private run uses no public inference server and releases aggregate statistics only. Model API submissions require a stable version and a plan that does not expose held-out cases to uncontrolled retention or training.

The pilot does not accept a competitive rank. Results may be displayed as provisional receipts. The model used for case authoring is flagged as an author consistency baseline, not a competitor. We do not accept hand-copied vendor leaderboard values as measured OGB scores.

Scope differs across guards: content moderation, prompt injection and arbitrary policy enforcement are separate capabilities. Every submission must name its adapter. Fixed-taxonomy models receive a published text wrapper in the pilot; per-area results are essential for interpreting them.
