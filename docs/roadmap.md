# From pilot to a ranked OGB release

The 0.1 pilot establishes a complete reproducible path, balanced Chinese/English minimal pairs, separate public/same-skill/novel partitions, real open-weight model receipts, and private-data-safe publication. Its sample size and machine labels make it a development edition.

Before a ranked edition:

- Independently adjudicate labels and audit semantic duplicate/contamination risk.
- Broaden coverage beyond the first 12 skills: fraud, financial boundaries, misinformation, copyright, regulated goods, cyber abuse vs defensive use, adversarial encodings, long-context and multi-turn attacks, and output moderation in native conversation protocols.
- Add licensed public benchmark builders with pinned revisions and dataset-specific policies; keep generated OGB cases separate from third-party benchmark scores.
- Evaluate specialist injection classifiers separately from general policy guards. Distinguish scope mismatches and unsupported tasks.
- Run untuned reference models to validate private/public difficulty and freeze any scale calibration before ranking.
- Expand the sample size and report uncertainty before deciding ties. Shared-GPU pilot latency cannot serve as a production speed ranking.
- Add multilingual and multimodal boards only with appropriate inputs, adversarial controls and separate metrics.

No future coverage or performance result is implied by the current pilot.
