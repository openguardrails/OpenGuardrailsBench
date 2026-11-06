# OpenGuardrailsBench pilot results

Only actual model runs appear in `leaderboard.json`. Public predictions and their inference configuration live under `public/<run>/`. Private results are aggregate-only, and no private case identifiers, input text, hashes or raw outputs are exported.

Scores use the frozen 0.1 pilot suite. Machine-authored labels have not yet received independent human adjudication. The task is contextual policy classification under the published adapter; a fixed-taxonomy content guard is not assumed to support every policy skill.

Shared hardware latency is descriptive. Four-bit weights are labeled and must not be compared to full-precision latency as if they used identical inference conditions. Gated/access and load failures are recorded separately and never receive made-up scores.

Always-allow and always-block are sanity baselines. The author model's consistency run is not a competitive submission. A full score is absent when any required partition has incomplete valid-answer coverage.
