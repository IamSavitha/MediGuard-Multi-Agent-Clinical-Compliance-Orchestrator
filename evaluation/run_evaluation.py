"""Measure MediGuard on the synthetic benchmarks in evaluation/datasets/.

    python evaluation/generate_datasets.py           # once (deterministic)
    python evaluation/run_evaluation.py              # PHI + retrieval + LLM coverage + end-to-end latency
    python evaluation/run_evaluation.py --skip-llm   # PHI + retrieval only (no model needed)

LLM steps use whatever get_llm() is configured for (LLM_PROVIDER=ollama|openai, OLLAMA_MODEL / OPENAI_MODEL).
Results: evaluation/results/metrics.json and evaluation/RESULTS.md.
"""
import argparse
import json
import os
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EVAL = ROOT / "evaluation"
DATA = EVAL / "datasets"
RESULTS = EVAL / "results"

# PHI types the regex detector is designed to catch (others in the benchmark are HIPAA identifiers it does not target).
TARGET_TYPES = {"name", "ssn", "phone", "email", "date", "mrn", "account_number", "credit_card"}

# Last commit before the PHI detector was improved; its detector is scored as the "before" baseline.
PHI_BASELINE_REF = "7eccd7c"


def load_baseline_detector():
    """Import PHIDetector from PHI_BASELINE_REF via git, without touching the working tree."""
    import subprocess
    import types
    src = subprocess.run(["git", "-C", str(ROOT), "show", f"{PHI_BASELINE_REF}:mediaguard/guardrails/phi_detector.py"],
                         capture_output=True, text=True, check=True).stdout
    mod = types.ModuleType("phi_detector_baseline")
    exec(compile(src, "phi_detector_baseline", "exec"), mod.__dict__)
    return mod.PHIDetector


def load_jsonl(path):
    return [json.loads(line) for line in open(path)]


def pct(x):
    return round(100.0 * x, 1)


# --------------------------------------------------------------------------- PHI
def eval_phi(dataset="phi_benchmark.jsonl", detector_cls=None):
    if detector_cls is None:
        from mediaguard.guardrails.phi_detector import PHIDetector as detector_cls

    docs = load_jsonl(DATA / dataset)
    det = detector_cls()
    caught, total = Counter(), Counter()
    tp_pred = fp_pred = 0
    fp_examples = Counter()
    docs_clean = docs_clean_target = 0
    t0 = time.perf_counter()

    for d in docs:
        text, gold = d["text"], d["spans"]
        found = det.detect_phi(text)
        pred = [(i["start"], i["end"], i["value"]) for k, v in found.items() if isinstance(v, list) for i in v]

        covered = [False] * len(text)
        for s, e, _ in pred:
            for k in range(s, e):
                covered[k] = True

        for g in gold:
            total[g["type"]] += 1
            n = g["end"] - g["start"]
            if sum(covered[g["start"]:g["end"]]) >= 0.5 * n:
                caught[g["type"]] += 1

        for s, e, v in pred:
            if any(s < g["end"] and g["start"] < e for g in gold):
                tp_pred += 1
            else:
                fp_pred += 1
                fp_examples[v if len(v) < 40 else v[:37] + "..."] += 1

        redacted, _ = det.redact_phi(text)
        leaked = [g for g in gold if g["value"] in redacted]
        docs_clean += not leaked
        docs_clean_target += not [g for g in leaked if g["type"] in TARGET_TYPES]

    elapsed = time.perf_counter() - t0
    all_caught, all_total = sum(caught.values()), sum(total.values())
    tgt_caught = sum(caught[t] for t in TARGET_TYPES)
    tgt_total = sum(total[t] for t in TARGET_TYPES)
    precision = tp_pred / (tp_pred + fp_pred) if tp_pred + fp_pred else 0.0
    recall_t = tgt_caught / tgt_total if tgt_total else 0.0
    return {
        "documents": len(docs),
        "gold_spans": all_total,
        "recall_all_hipaa_identifiers": pct(all_caught / all_total),
        "recall_target_types": pct(recall_t),
        "precision": pct(precision),
        "f1_target_types": pct(2 * precision * recall_t / (precision + recall_t)) if precision + recall_t else 0.0,
        "recall_by_type": {t: {"caught": caught[t], "total": total[t], "recall": pct(caught[t] / total[t])}
                           for t in sorted(total)},
        "false_positive_spans": fp_pred,
        "top_false_positives": fp_examples.most_common(6),
        "docs_fully_deidentified_pct": pct(docs_clean / len(docs)),
        "docs_deidentified_target_types_pct": pct(docs_clean_target / len(docs)),
        "ms_per_document": round(1000 * elapsed / len(docs), 2),
    }


# --------------------------------------------------------------------------- coverage
def build_store():
    from mediaguard.rag.vector_store import VectorStore
    from mediaguard.rag.policy_loader import load_policies

    store = VectorStore(provider="memory")
    load_policies(store, json.loads((DATA / "coverage_policies.json").read_text()))
    return store


def request_text(case):
    return f"{case['treatment']} for a member of the {case['plan_name']} ({case['policy_id']})"


def eval_retrieval(store, cases):
    hit1 = hit3 = 0
    for c in cases:
        ids = [r["id"] for r in store.search_similar(request_text(c), top_k=3)]
        hit1 += bool(ids) and ids[0] == c["policy_id"]
        hit3 += c["policy_id"] in ids
    return {"cases": len(cases), "hit_at_1": pct(hit1 / len(cases)), "hit_at_3": pct(hit3 / len(cases))}


def eval_coverage(store, cases, model):
    from mediaguard.agents.policy_validator import PolicyValidator

    v = PolicyValidator(model_name=model, vector_store=store)
    rows, latencies = [], []
    for c in cases:
        t0 = time.perf_counter()
        out = v.validate_treatment(request_text(c),
                                   patient_metadata={"insurance_plan": c["plan_name"], "policy_id": c["policy_id"]},
                                   claim_amount=c["claim_amount"])
        latencies.append(time.perf_counter() - t0)
        pred = bool(out.get("is_covered"))
        rows.append({"id": c["id"], "treatment": c["treatment_type"], "policy_id": c["policy_id"],
                     "gold": c["gold_covered"], "pred": pred,
                     "parse_failed": "Could not parse" in str(out.get("reasoning", "")),
                     "error": out.get("error")})
        print(f"  [{len(rows):2d}/{len(cases)}] {c['policy_id']} {c['treatment_type']:<28} gold={c['gold_covered']!s:<5} "
              f"pred={pred!s:<5} {latencies[-1]:.1f}s", flush=True)

    tp = sum(r["gold"] and r["pred"] for r in rows)
    tn = sum(not r["gold"] and not r["pred"] for r in rows)
    fp = sum(not r["gold"] and r["pred"] for r in rows)
    fn = sum(r["gold"] and not r["pred"] for r in rows)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "model": model,
        "cases": len(rows),
        "accuracy": pct((tp + tn) / len(rows)),
        "precision_covered": pct(prec),
        "recall_covered": pct(rec),
        "f1_covered": pct(2 * prec * rec / (prec + rec)) if prec + rec else 0.0,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "unparseable_responses": sum(r["parse_failed"] for r in rows),
        "errors": sum(bool(r["error"]) for r in rows),
        "median_seconds_per_decision": round(statistics.median(latencies), 2),
        "rows": rows,
    }


CLAIM_TEMPLATE = """MEDICAL CLAIM

Patient Information:
Name: {name}
DOB: 04/12/1978
Member ID: XGH{member}
Insurance: {plan_name} ({policy_id})

Treatment Details:
Date of Service: 03/18/2025
Provider: City Medical Center
Treatment: {treatment}

Billing:
Total Amount: ${amount:,}.00
"""


def eval_end_to_end(store, cases, model, n):
    from mediaguard.orchestrator import MediGuardOrchestrator

    orch = MediGuardOrchestrator(model_name=model, vector_store=store)
    times, statuses = [], Counter()
    names = ["Grace Kim", "Omar Haddad", "Elena Rossi", "Liam Murphy", "Priya Patel", "Noah Silva", "Mei Tanaka", "Zara Osei"]
    for i, c in enumerate(cases[:n]):
        doc = CLAIM_TEMPLATE.format(name=names[i % len(names)], member=100000000 + i, plan_name=c["plan_name"],
                                    policy_id=c["policy_id"], treatment=c["treatment"], amount=c["claim_amount"])
        t0 = time.perf_counter()
        out = orch.process_document(doc, document_id=f"e2e-{i}")
        times.append(time.perf_counter() - t0)
        statuses[str(out.get("status", "unknown"))] += 1
        print(f"  [e2e {i + 1}/{n}] {times[-1]:.1f}s status={out.get('status')}", flush=True)
    return {
        "model": model,
        "claims": len(times),
        "median_seconds_per_claim": round(statistics.median(times), 1),
        "p90_seconds_per_claim": round(sorted(times)[max(0, int(0.9 * len(times)) - 1)], 1),
        "statuses": dict(statuses),
    }


# --------------------------------------------------------------------------- report
def bias_pattern_count():
    from mediaguard.guardrails.bias_detector import BiasDetector
    return {k: len(v) for k, v in BiasDetector.BIAS_PATTERNS.items()}


def write_report(m):
    phi, ret = m["phi"], m["retrieval"]
    lines = [
        "# MediGuard evaluation results",
        "",
        f"_Generated {m['generated_at']} on {m['machine']}. Reproduce with `python evaluation/generate_datasets.py && "
        "python evaluation/run_evaluation.py`._",
        "",
        "All data is synthetic and generated deterministically by `evaluation/generate_datasets.py`.",
        "",
        "## PHI detection and redaction (regex guardrail)",
        "",
        f"Benchmark: {phi['documents']} documents (claim forms, clinical notes, billing JSON) with {phi['gold_spans']} gold "
        "PHI spans labeled per HIPAA Safe Harbor, plus non-PHI look-alikes (CPT/ICD codes, NPIs, claim IDs, tax IDs, amounts).",
        "",
        f"Held-out set: {m['phi_holdout']['documents']} documents of different types (discharge summaries, referral letters, "
        f"portal messages) with {m['phi_holdout']['gold_spans']} spans, never used while changing the detector.",
        "",
        f"Before = detector at commit `{m['phi_baseline']['ref']}`; after = current detector.",
        "",
        "| | Main: before | Main: after | Held-out: before | Held-out: after |",
        "|---|---:|---:|---:|---:|",
    ]
    b_main, b_hold, hold = m["phi_baseline"]["main"], m["phi_baseline"]["holdout"], m["phi_holdout"]
    for label, key in [("Recall, target types", "recall_target_types"), ("Recall, all HIPAA identifiers", "recall_all_hipaa_identifiers"),
                       ("Precision", "precision"), ("F1, target types", "f1_target_types"),
                       ("Docs with no target-type PHI left after redaction", "docs_deidentified_target_types_pct"),
                       ("Docs fully de-identified", "docs_fully_deidentified_pct")]:
        lines.append(f"| {label} | {b_main[key]}% | **{phi[key]}%** | {b_hold[key]}% | **{hold[key]}%** |")
    if m.get("phi_independent"):
        ind, b_ind = m["phi_independent"], m["phi_baseline"]["independent"]
        lines += [
            "",
            "### Independent test (LLM-written documents)",
            "",
            f"The two sets above were written by the same person who tuned the detector, so near-perfect scores there mostly "
            f"show the patterns cover those formats. For an independent check, a local LLM wrote {ind['documents']} free-form "
            f"documents (ER notes, referral emails, appeal letters, faxes, ...) with {ind['gold_spans']} PHI values it listed "
            "itself (`evaluation/generate_llm_phi_set.py`). The model's list can miss identifiers, so precision is not "
            "meaningful here; recall and leakage are.",
            "",
            "| | Before | After |",
            "|---|---:|---:|",
            f"| Recall, all listed identifiers | {b_ind['recall_all_hipaa_identifiers']}% | **{ind['recall_all_hipaa_identifiers']}%** |",
            f"| Documents with no listed PHI left after redaction | {b_ind['docs_fully_deidentified_pct']}% | **{ind['docs_fully_deidentified_pct']}%** |",
            "",
            "| Type | Caught / total | Recall |",
            "|---|---:|---:|",
        ]
        for t, r in ind["recall_by_type"].items():
            lines.append(f"| {t} | {r['caught']} / {r['total']} | {r['recall']}% |")
    lines += [
        "",
        "Main benchmark, current detector:",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Recall, types the detector targets | {phi['recall_target_types']}% |",
        f"| Recall, all HIPAA identifiers in the benchmark | {phi['recall_all_hipaa_identifiers']}% |",
        f"| Precision (predicted spans that are PHI) | {phi['precision']}% |",
        f"| F1, target types | {phi['f1_target_types']}% |",
        f"| Documents with no target-type PHI left after redaction | {phi['docs_deidentified_target_types_pct']}% |",
        f"| Documents fully de-identified (all identifiers) | {phi['docs_fully_deidentified_pct']}% |",
        f"| Speed | {phi['ms_per_document']} ms / document |",
        "",
        "| PHI type | Caught / total | Recall |",
        "|---|---:|---:|",
    ]
    for t, r in phi["recall_by_type"].items():
        lines.append(f"| {t}{'' if t in TARGET_TYPES else ' *(not targeted)*'} | {r['caught']} / {r['total']} | {r['recall']}% |")
    lines += ["", "| Held-out PHI type | Caught / total | Recall |", "|---|---:|---:|"]
    for t, r in hold["recall_by_type"].items():
        lines.append(f"| {t}{'' if t in TARGET_TYPES else ' *(not targeted)*'} | {r['caught']} / {r['total']} | {r['recall']}% |")
    fps = phi["top_false_positives"] + hold["top_false_positives"]
    lines += ["", ("Most frequent false positives: " + ", ".join(f"`{v}` ×{n}" for v, n in fps[:8])) if fps
              else "No false-positive spans on either set.", ""]
    lines += [
        "## Policy retrieval (RAG)",
        "",
        f"{ret['cases']} treatment requests against {m['policies']} policies, all-MiniLM-L6-v2 embeddings, cosine similarity.",
        "",
        f"| Hit@1 | Hit@3 |\n|---:|---:|\n| {ret['hit_at_1']}% | {ret['hit_at_3']}% |",
        "",
    ]
    for cov in m.get("coverage", []):
        lines += [
            f"## Coverage decisions: PolicyValidator ({cov['model']})",
            "",
            f"{cov['cases']} labeled cases ({cov['confusion']['tp'] + cov['confusion']['fn']} covered, "
            f"{cov['confusion']['tn'] + cov['confusion']['fp']} excluded or not listed).",
            "",
            "| Accuracy | Precision (covered) | Recall (covered) | F1 | Unparseable replies | Median time |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {cov['accuracy']}% | {cov['precision_covered']}% | {cov['recall_covered']}% | {cov['f1_covered']}% | "
            f"{cov['unparseable_responses']} | {cov['median_seconds_per_decision']} s |",
            "",
        ]
    if m.get("end_to_end"):
        e = m["end_to_end"]
        lines += [
            f"## End-to-end pipeline ({e['model']})",
            "",
            f"Triage → policy validation → compliance audit on {e['claims']} claims: median **{e['median_seconds_per_claim']} s** "
            f"per claim (p90 {e['p90_seconds_per_claim']} s). Statuses: {e['statuses']}.",
            "",
        ]
    lines += [
        "## Bias guardrail",
        "",
        f"The bias detector checks {sum(m['bias_patterns'].values())} sensitive attributes across "
        f"{len(m['bias_patterns'])} categories: " + ", ".join(f"{k} ({v})" for k, v in m["bias_patterns"].items()) + ".",
        "",
    ]
    (EVAL / "RESULTS.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument("--models", default=os.getenv("OLLAMA_MODEL", "llama3.2"),
                    help="comma-separated model names for the coverage benchmark")
    ap.add_argument("--e2e", type=int, default=8, help="claims for the end-to-end latency run (0 to skip)")
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    m = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
         "machine": f"{platform.system()} {platform.machine()}",
         "llm_provider": os.getenv("LLM_PROVIDER", "openai")}

    print("PHI benchmark...")
    baseline = load_baseline_detector()
    m["phi"] = eval_phi()
    m["phi_holdout"] = eval_phi("phi_holdout.jsonl")
    m["phi_baseline"] = {"ref": PHI_BASELINE_REF, "main": eval_phi(detector_cls=baseline),
                         "holdout": eval_phi("phi_holdout.jsonl", detector_cls=baseline)}
    if (DATA / "phi_llm_independent.jsonl").exists():
        m["phi_independent"] = eval_phi("phi_llm_independent.jsonl")
        m["phi_baseline"]["independent"] = eval_phi("phi_llm_independent.jsonl", detector_cls=baseline)
        print(f"  independent (LLM-written) recall={m['phi_independent']['recall_all_hipaa_identifiers']}% "
              f"(baseline {m['phi_baseline']['independent']['recall_all_hipaa_identifiers']}%)")
    for name, r in [("main", m["phi"]), ("holdout", m["phi_holdout"]),
                    ("baseline main", m["phi_baseline"]["main"]), ("baseline holdout", m["phi_baseline"]["holdout"])]:
        print(f"  {name:<17} recall(target)={r['recall_target_types']}% precision={r['precision']}% "
              f"clean docs={r['docs_deidentified_target_types_pct']}%")

    cases = load_jsonl(DATA / "coverage_benchmark.jsonl")
    store = build_store()
    m["policies"] = store.count()
    print("Retrieval benchmark...")
    m["retrieval"] = eval_retrieval(store, cases)
    print(f"  hit@1={m['retrieval']['hit_at_1']}% hit@3={m['retrieval']['hit_at_3']}%")
    m["bias_patterns"] = bias_pattern_count()

    if not args.skip_llm:
        m["coverage"] = []
        for model in [x.strip() for x in args.models.split(",") if x.strip()]:
            print(f"Coverage benchmark with {model}...")
            m["coverage"].append(eval_coverage(store, cases, model))
        if args.e2e:
            model = args.models.split(",")[0].strip()
            print(f"End-to-end latency with {model}...")
            m["end_to_end"] = eval_end_to_end(store, cases, model, args.e2e)

    (RESULTS / "metrics.json").write_text(json.dumps(m, indent=2))
    write_report(m)
    print(f"\nWrote {RESULTS / 'metrics.json'} and {EVAL / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
