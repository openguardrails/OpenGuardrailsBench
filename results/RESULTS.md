# OGB 0.1 synthetic pilot results

Measured on the frozen 480-case suite. Machine-authored labels with editorial corrections; independent human adjudication pending. This is contextual policy classification under a published text wrapper, not a native vendor benchmark. These are provisional receipts, without competitive ranks.

| Model | Public | Private same | Private novel | Full | Complete answers |
|---|---:|---:|---:|---:|---:|
| nvidia/Nemotron-Content-Safety-Reasoning-4B (NF4) | 76.56 | 77.86 | 52.08 | 67.55 | 480/480 |
| Qwen/Qwen3Guard-Gen-4B (NF4) | 57.03 | 67.19 | 25.00 | 50.31 | 480/480 |
| Qwen/Qwen3Guard-Gen-0.6B | 33.33 | 38.28 | 10.42 | 27.14 | 480/480 |
| allow-all | 0.00 | 0.00 | 0.00 | 0.00 | 480/480 |
| block-all | 0.00 | 0.00 | 0.00 | 0.00 | 480/480 |
| meta-llama/Llama-Guard-3-1B | 0.00 | 0.00 | 0.00 | 0.00 | 480/480 |
| nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3 (NF4) | 57.29 | 64.84 | 25.00 | — | 479/480 |

Full = 60% private same + 40% private novel, with complete valid answers on all three partitions. A malformed or truncated response loses credit and prevents Full eligibility. All-zero Llama Guard results apply to this policy/context wrapper and must not be interpreted as a measurement of its native moderation benchmark. Shared-machine latency does not establish speed ranks.

Exact model commits, quantization, package versions and public raw predictions are included in `public/`. Held-out inputs and raw outputs remain private.
