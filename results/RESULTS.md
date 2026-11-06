# OGB 0.1 synthetic pilot results

Measured on the frozen 480-case suite. Machine-authored labels with editorial corrections; independent human adjudication pending. This is contextual policy classification under a published text wrapper, not a native vendor benchmark. These are provisional receipts, without competitive ranks.

| Model | Public | Private same | Private novel | Full | Valid answers | Run status |
|---|---:|---:|---:|---:|---:|---|
| OpenGuardrails (maintainer-owned) | 89.84 | 93.75 | 91.67 | 92.92 | 480/480 | Completed |
| nvidia/Nemotron-Content-Safety-Reasoning-4B (NF4) | 76.56 | 77.86 | 52.08 | 67.55 | 480/480 | Completed |
| Qwen/Qwen3Guard-Gen-4B (NF4) | 57.03 | 67.19 | 25.00 | 50.31 | 480/480 | Completed |
| Qwen/Qwen3Guard-Gen-0.6B | 33.33 | 38.28 | 10.42 | 27.14 | 480/480 | Completed |
| allow-all | 0.00 | 0.00 | 0.00 | 0.00 | 480/480 | Completed; all predictions safe |
| block-all | 0.00 | 0.00 | 0.00 | 0.00 | 480/480 | Completed |
| meta-llama/Llama-Guard-3-1B | 0.00 | 0.00 | 0.00 | 0.00 | 480/480 | Completed; all predictions safe |
| nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3 (NF4) | 57.29 | 64.84 | 25.00 | Not eligible | 479/480 | Finished; 1 invalid, 0 errors |

Full = 60% private same + 40% private novel, with complete valid answers on all three partitions. A malformed or truncated response loses credit and prevents Full eligibility. All-zero Llama Guard results apply to this policy/context wrapper and must not be interpreted as a measurement of its native moderation benchmark. Shared-machine latency does not establish speed ranks.

OpenGuardrails is for builders; AIRS is the enterprise edition. Both share the same safety capability. The OpenGuardrails entry evaluates that shared capability through a typed decision interface with a frozen threshold of 0.5. It is maintainer-owned and self-evaluated. Deployment fingerprints are retained; backend aliases are redacted from public receipts. This run does not measure every product integration or enterprise workflow.

Exact model commits, quantization, package versions and public raw predictions are included in `public/`. Held-out inputs and raw outputs remain private.
