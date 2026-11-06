# Maintainer workflow

1. Run `python scripts/generate_suite.py --novel-tracks private/tracks.json` on t3090 against the existing Qwen endpoint. Never interrupt the serving process. All generated drafts and receipts go to ignored `work/authoring`.
2. Author same-skill held-outs independently. Keep novel domain briefs in `private/tracks.json`, outside the public repository. Keep pairs together.
3. Validate the combined file. Review labels and semantic leakage independently before changing pilot status. Record the real served-model path and deployment receipt; a served alias alone is insufficient for a final release.
4. Copy only the public JSONL into `data/public/ogb-0.1.jsonl`. Store held-outs in ignored `private/`. Freeze manifest hashes. Run `python scripts/check_release.py`.
5. Evaluate models with `scripts/run_models.py --rows private/all.jsonl`. This runs models sequentially with bounded GPU memory. No service shutdown or GPU eviction is authorized by this script. Load/download/access failures have explicit receipts.
6. Export public raw results and aggregate-only private results with `scripts/export_results.py`. A public result must not carry private case IDs, input hashes or text.
7. `python scripts/publish_hf.py` creates a public dataset `openguardrails/OpenGuardrailsBench`, a **private** dataset `openguardrails/OpenGuardrailsBench-private`, and the static leaderboard Space `openguardrails/OpenGuardrailsBench`. Existing private repo visibility is checked before uploading. The script uses only an explicit file allowlist and never uploads the checkout directory.

`HF_TOKEN` is read from the environment or the standard Hugging Face credential store. Never persist credentials in code or command arguments. Run the publisher only from the intended checkout after reviewing the exported summaries. Public Space uses static HTML/JavaScript; it never loads private cases or exposes an inference endpoint.

Private manifests and full outputs stay in the private dataset; the Space receives a sanitized aggregate leaderboard. Public score visibility is distinct from public case visibility. Do not publish the full authoring log or full result file from the combined suite.
