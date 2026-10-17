# MediGuard evaluation results

_Generated 2026-10-16 23:39 on Darwin arm64. Reproduce with `python evaluation/generate_datasets.py && python evaluation/run_evaluation.py`._

All data is synthetic and generated deterministically by `evaluation/generate_datasets.py`.

## PHI detection and redaction (regex guardrail)

Benchmark: 240 documents (claim forms, clinical notes, billing JSON) with 1600 gold PHI spans labeled per HIPAA Safe Harbor, plus non-PHI look-alikes (CPT/ICD codes, NPIs, claim IDs, tax IDs, amounts).

Held-out set: 120 documents of different types (discharge summaries, referral letters, portal messages) with 920 spans, never used while changing the detector.

Before = detector at commit `7eccd7c`; after = current detector.

| | Main: before | Main: after | Held-out: before | Held-out: after |
|---|---:|---:|---:|---:|
| Recall, target types | 73.2% | **100.0%** | 42.8% | **100.0%** |
| Recall, all HIPAA identifiers | 62.2% | **100.0%** | 35.3% | **100.0%** |
| Precision | 82.8% | **100.0%** | 90.1% | **100.0%** |
| F1, target types | 77.7% | **100.0%** | 58.0% | **100.0%** |
| Docs with no target-type PHI left after redaction | 33.3% | **100.0%** | 0.0% | **100.0%** |
| Docs fully de-identified | 33.3% | **100.0%** | 0.0% | **100.0%** |

Main benchmark, current detector:

| Metric | Value |
|---|---:|
| Recall, types the detector targets | 100.0% |
| Recall, all HIPAA identifiers in the benchmark | 100.0% |
| Precision (predicted spans that are PHI) | 100.0% |
| F1, target types | 100.0% |
| Documents with no target-type PHI left after redaction | 100.0% |
| Documents fully de-identified (all identifiers) | 100.0% |
| Speed | 0.36 ms / document |

| PHI type | Caught / total | Recall |
|---|---:|---:|
| account_number | 80 / 80 | 100.0% |
| address *(not targeted)* | 160 / 160 | 100.0% |
| credit_card | 80 / 80 | 100.0% |
| date | 400 / 400 | 100.0% |
| email | 80 / 80 | 100.0% |
| member_id *(not targeted)* | 80 / 80 | 100.0% |
| mrn | 160 / 160 | 100.0% |
| name | 320 / 320 | 100.0% |
| phone | 160 / 160 | 100.0% |
| ssn | 80 / 80 | 100.0% |

| Held-out PHI type | Caught / total | Recall |
|---|---:|---:|
| address *(not targeted)* | 80 / 80 | 100.0% |
| credit_card | 40 / 40 | 100.0% |
| date | 240 / 240 | 100.0% |
| email | 80 / 80 | 100.0% |
| member_id *(not targeted)* | 80 / 80 | 100.0% |
| mrn | 80 / 80 | 100.0% |
| name | 200 / 200 | 100.0% |
| phone | 120 / 120 | 100.0% |

No false-positive spans on either set.

## Policy retrieval (RAG)

42 treatment requests against 6 policies, all-MiniLM-L6-v2 embeddings, cosine similarity.

| Hit@1 | Hit@3 |
|---:|---:|
| 71.4% | 83.3% |

## Bias guardrail

The bias detector checks 18 sensitive attributes across 4 categories: demographic (7), socioeconomic (4), geographic (4), treatment (3).
