"""Generate an independent PHI test set with a local LLM (not written by the detector's author).

A model writes free-form fictional clinical documents and lists the PHI values it included.
Only listed values that appear verbatim in the text are kept as gold. Because the model's list can
miss identifiers, use this set for recall / leak rate, not precision.

    ollama pull llama3.2
    python evaluation/generate_llm_phi_set.py --n 60
"""
import argparse
import json
import random
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "datasets" / "phi_llm_independent.jsonl"
DOC_TYPES = ["emergency department note", "referral email between two clinics", "insurance appeal letter written by a patient",
             "nursing handoff note", "telehealth visit summary", "pharmacy prior-authorization fax",
             "hospital billing dispute email", "physical therapy intake form", "lab results message to a patient",
             "home health visit report"]
TYPE_MAP = {"name": "name", "patient_name": "name", "date_of_birth": "date", "dob": "date", "date": "date",
            "visit_date": "date", "phone": "phone", "phone_number": "phone", "email": "email", "mrn": "mrn",
            "medical_record_number": "mrn", "address": "address", "street_address": "address", "zip": "address",
            "zip_code": "address", "member_id": "member_id", "insurance_id": "member_id", "ssn": "ssn",
            "account_number": "account_number", "credit_card": "credit_card"}

PROMPT = """Write a realistic but entirely fictional {doc} from a US healthcare setting, 120-220 words.
Naturally include these identifiers for ONE fictional patient, using formats you choose freely:
full name (mention it at least twice, once in running text), date of birth, one other date (visit/admission),
phone number, email address, medical record number, street address with city, state and ZIP code,
and an insurance member ID. You may also include provider names, NPI numbers, CPT/ICD codes and amounts.

Return JSON only: {{"text": "<the document>", "phi": [{{"type": "<one of: name, date_of_birth, date, phone,
email, mrn, address, zip, member_id>", "value": "<exact substring copied from text>"}}]}}
List every occurrence of the patient's name separately. Copy values character-for-character."""


def ask(model, prompt, seed):
    body = json.dumps({"model": model, "prompt": prompt, "format": "json", "stream": False,
                       "options": {"temperature": 0.8, "seed": seed, "num_predict": 900}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(json.loads(r.read())["response"])


def to_spans(text, phi):
    spans, used = [], []
    for item in phi:
        value = str(item.get("value", "")).strip()
        kind = TYPE_MAP.get(str(item.get("type", "")).lower().replace(" ", "_"))
        if not value or not kind or len(value) < 3:
            continue
        start = 0
        while True:  # next unused occurrence of this exact value
            i = text.find(value, start)
            if i < 0:
                break
            if not any(i < e and s < i + len(value) for s, e in used):
                spans.append({"start": i, "end": i + len(value), "type": kind, "value": value})
                used.append((i, i + len(value)))
                break
            start = i + 1
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--model", default="llama3.2")
    args = ap.parse_args()
    rng = random.Random(7)
    rows = []
    for i in range(args.n):
        doc = DOC_TYPES[i % len(DOC_TYPES)]
        try:
            out = ask(args.model, PROMPT.format(doc=doc), seed=rng.randint(1, 10**6))
            text = str(out.get("text", ""))
            spans = to_spans(text, out.get("phi") or [])
        except Exception as e:  # malformed JSON etc.
            print(f"  [{i + 1}/{args.n}] skipped: {e}")
            continue
        if len(text) < 200 or len(spans) < 4:
            print(f"  [{i + 1}/{args.n}] skipped: too few verified PHI values")
            continue
        rows.append({"id": f"llm-{i:03d}", "kind": doc, "generator": args.model, "text": text, "spans": spans})
        print(f"  [{i + 1}/{args.n}] {doc}: {len(spans)} PHI spans", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    print(f"Wrote {len(rows)} documents, {sum(len(r['spans']) for r in rows)} spans -> {OUT}")


if __name__ == "__main__":
    main()
