"""Generate the synthetic evaluation datasets (deterministic, fixed seed).

Outputs (in evaluation/datasets/):
- phi_benchmark.jsonl      documents with gold PHI spans (HIPAA Safe Harbor identifiers) plus
                           look-alike non-PHI distractors (CPT/ICD codes, NPIs, claim IDs, amounts)
- phi_holdout.jsonl        held-out PHI set with different document types and formats
- coverage_policies.json   policy library used for the coverage benchmark
- coverage_benchmark.jsonl treatment requests with the gold policy and gold covered / not-covered label

All people, numbers and policies are fictional.
"""
import json
import random
from pathlib import Path

SEED = 20261017
OUT = Path(__file__).parent / "datasets"

FIRST = ["James", "Maria", "Wei", "Aisha", "Carlos", "Priya", "Daniel", "Fatima", "Liam", "Sofia",
         "Hiroshi", "Grace", "Omar", "Elena", "Noah", "Amara", "Lucas", "Mei", "Ethan", "Zara"]
LAST = ["Alvarez", "Nguyen", "Okafor", "Patel", "Kowalski", "Haddad", "Johansson", "Reyes", "Tanaka",
        "Murphy", "Schmidt", "Osei", "Rossi", "Kim", "Fischer", "Mendoza", "Novak", "Silva", "Ahmed", "Brooks"]
STREETS = ["Maple Ave", "Oak Street", "Sunset Blvd", "Willow Lane", "Cedar Road", "Elm Court", "Park Drive"]
CITIES = [("San Jose", "CA", "95112"), ("Austin", "TX", "78701"), ("Denver", "CO", "80202"),
          ("Seattle", "WA", "98101"), ("Columbus", "OH", "43215"), ("Raleigh", "NC", "27601")]
PROVIDERS = ["City Medical Center", "Valley Orthopedics", "Northside Imaging", "Bayview Clinic", "St. Anne Hospital"]
PROCEDURES = [("99213", "M54.5", "office visit for low back pain"), ("70551", "R51.9", "MRI brain without contrast"),
              ("71046", "J18.9", "chest X-ray, 2 views"), ("29881", "S83.241A", "knee arthroscopy with meniscectomy"),
              ("90837", "F41.1", "psychotherapy, 60 minutes"), ("93000", "I48.91", "electrocardiogram")]


class Doc:
    """Builds text while recording gold PHI spans."""

    def __init__(self):
        self.parts, self.spans, self.pos = [], [], 0

    def text(self, s):
        self.parts.append(s)
        self.pos += len(s)

    def phi(self, s, kind):
        self.spans.append({"start": self.pos, "end": self.pos + len(s), "type": kind, "value": s})
        self.text(s)

    def build(self):
        return "".join(self.parts), self.spans


def rnd_digits(r, n):
    return "".join(str(r.randint(0, 9)) for _ in range(n))


def phone(r):
    a, b, c = r.randint(201, 989), r.randint(200, 999), rnd_digits(r, 4)
    return r.choice([f"{a}-{b}-{c}", f"{a}.{b}.{c}", f"({a}) {b}-{c}", f"{a}{b}{c}"])


def date_mdy(r, y0, y1):
    return f"{r.randint(1, 12):02d}/{r.randint(1, 28):02d}/{r.randint(y0, y1)}"


def date_long(r, y0, y1):
    months = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
    return f"{r.choice(months)} {r.randint(1, 28)}, {r.randint(y0, y1)}"


def claim_form(r):
    d = Doc()
    first, last = r.choice(FIRST), r.choice(LAST)
    cpt, icd, desc = r.choice(PROCEDURES)
    city, st, z = r.choice(CITIES)
    d.text("MEDICAL CLAIM\n\nPatient Information:\nName: ")
    d.phi(f"{first} {last}", "name")
    d.text("\nDOB: ")
    d.phi(date_mdy(r, 1940, 2010), "date")
    d.text("\nSSN: ")
    d.phi(f"{rnd_digits(r, 3)}-{rnd_digits(r, 2)}-{rnd_digits(r, 4)}", "ssn")
    d.text("\nPhone: ")
    d.phi(phone(r), "phone")
    d.text("\nAddress: ")
    d.phi(f"{r.randint(10, 9999)} {r.choice(STREETS)}", "address")
    d.text(f", {city}, {st} ")
    d.phi(z, "address")
    d.text("\nMember ID: ")
    d.phi(f"{r.choice(['XGH', 'BCX', 'UHC'])}{rnd_digits(r, 9)}", "member_id")
    d.text("\nMRN: ")
    d.phi(rnd_digits(r, 7), "mrn")
    d.text(f"\n\nTreatment Details:\nDate of Service: ")
    d.phi(date_mdy(r, 2024, 2025), "date")
    d.text(f"\nProvider: {r.choice(PROVIDERS)}\nProvider NPI: {rnd_digits(r, 10)}\n")
    d.text(f"CPT: {cpt}   ICD-10: {icd}\nTreatment: {desc}\n\n")
    d.text(f"Billing:\nClaim ID: CLM-{r.randint(2024, 2025)}-{rnd_digits(r, 5)}\n")
    d.text(f"Total Amount: ${r.randint(120, 9800):,}.00\nTax ID: {rnd_digits(r, 2)}-{rnd_digits(r, 7)}\n")
    return d.build()


def clinical_note(r):
    d = Doc()
    first, last = r.choice(FIRST), r.choice(LAST)
    cpt, icd, desc = r.choice(PROCEDURES)
    d.text("PROGRESS NOTE\nPatient: ")
    d.phi(f"{first} {last}", "name")
    d.text("   MRN: ")
    d.phi(rnd_digits(r, 8), "mrn")
    d.text("\nVisit date: ")
    d.phi(date_mdy(r, 2024, 2025), "date")
    d.text(f"\n\nS: ")
    d.phi(f"Mr. {last}" if r.random() < 0.5 else f"Ms. {last}", "name")
    d.text(f" presents for {desc}. Reports symptoms for {r.randint(2, 20)} days. ")
    d.text("Born on ")
    d.phi(date_long(r, 1945, 2005), "date")
    d.text(f".\nO: BP {r.randint(105, 150)}/{r.randint(65, 95)}, HR {r.randint(58, 100)}, ")
    d.text(f"BMI {r.randint(19, 38)}.{r.randint(0, 9)}.\nA/P: {icd}. Order {cpt}. Follow up in {r.randint(1, 6)} weeks.\n")
    d.text("Contact: ")
    d.phi(f"{first.lower()}.{last.lower()}{r.randint(1, 99)}@{r.choice(['gmail.com', 'outlook.com', 'example.org'])}", "email")
    d.text(" or ")
    d.phi(phone(r), "phone")
    d.text(f"\nSigned: Dr. {r.choice(LAST)}, NPI {rnd_digits(r, 10)}\n")
    return d.build()


def billing_json(r):
    d = Doc()
    first, last = r.choice(FIRST), r.choice(LAST)
    cpt, icd, _ = r.choice(PROCEDURES)
    d.text('{\n  "patient_name": "')
    d.phi(f"{first} {last}", "name")
    d.text('",\n  "account": "Account ')
    d.phi(rnd_digits(r, 8), "account_number")
    d.text('",\n  "card_on_file": "')
    groups = [rnd_digits(r, 4) for _ in range(4)]
    d.phi(r.choice(["-", " "]).join(groups), "credit_card")
    d.text(f'",\n  "cpt": "{cpt}",\n  "icd10": "{icd}",\n  "amount_due": {r.randint(40, 4000)}.{r.randint(10, 99)},\n')
    d.text(f'  "claim_number": "{rnd_digits(r, 9)}",\n  "service_date": "')
    d.phi(date_mdy(r, 2024, 2025), "date")
    d.text('"\n}\n')
    return d.build()


def make_phi(r, n=240):
    builders = [claim_form, clinical_note, billing_json]
    rows = []
    for i in range(n):
        text, spans = builders[i % 3](r)
        rows.append({"id": f"phi-{i:03d}", "kind": builders[i % 3].__name__, "text": text, "spans": spans})
    return rows


# --- Held-out PHI set: different document types, labels and formats from the main benchmark.
# Used to check that detector changes generalize instead of fitting the main benchmark's templates.
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def discharge_summary(r):
    d = Doc()
    first, last = r.choice(FIRST), r.choice(LAST)
    city, st, z = r.choice(CITIES)
    d.text("DISCHARGE SUMMARY\nPatient Name: ")
    d.phi(f"{first} {last}", "name")
    d.text("\nD.O.B.: ")
    d.phi(f"{r.randint(1, 12)}/{r.randint(1, 28)}/{r.randint(1940, 2005)}", "date")
    d.text("\nMedical Record #: ")
    d.phi(f"00{rnd_digits(r, 6)}", "mrn")
    d.text("\nAdmitted: ")
    d.phi(f"{r.randint(2024, 2025)}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}", "date")
    d.text("   Discharged: ")
    d.phi(f"{r.randint(2024, 2025)}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}", "date")
    d.text("\nHome address: ")
    d.phi(f"{r.randint(1, 999)} {r.choice(['Birch', 'Pine', 'Lakeview', 'Hillcrest'])} {r.choice(['St.', 'Ave.', 'Rd.'])}", "address")
    d.text(f", {city}, {st} ")
    d.phi(z, "address")
    d.text("\nTel: ")
    d.phi(f"+1 {r.randint(201, 989)} {r.randint(200, 999)} {rnd_digits(r, 4)}", "phone")
    d.text("\nInsurance ID: ")
    d.phi(f"AET-{rnd_digits(r, 8)}", "member_id")
    d.text(f"\nAttending: Dr. {r.choice(LAST)} (NPI {rnd_digits(r, 10)})   Room {r.randint(100, 899)}   DRG {r.randint(100, 999)}\n")
    d.text("Hospital course unremarkable; discharged home in stable condition.\n")
    return d.build()


def referral_letter(r):
    d = Doc()
    first, last = r.choice(FIRST), r.choice(LAST)
    _, icd, desc = r.choice(PROCEDURES)
    d.text("Re: ")
    d.phi(f"{first} {last}", "name")
    d.text(" (DOB ")
    d.phi(f"{r.randint(1, 12):02d}-{r.randint(1, 28):02d}-{r.randint(1940, 2005)}", "date")
    d.text(")\n\nDear Dr. " + r.choice(LAST) + ",\n\nI am referring my patient, ")
    d.phi(f"{first} {last}", "name")
    d.text(f", for evaluation of {desc} ({icd}). MRN ")
    d.phi(rnd_digits(r, 8), "mrn")
    d.text(". Symptoms began on ")
    d.phi(date_mdy(r, 2024, 2025), "date")
    d.text(f". Prior authorization ref PA-{rnd_digits(r, 6)}.\nThe patient can be reached at ")
    d.phi(f"{first[0].lower()}{last.lower()}@{r.choice(['yahoo.com', 'icloud.com', 'example.net'])}", "email")
    d.text(" or ")
    d.phi(f"{r.randint(201, 989)}.{r.randint(200, 999)}.{rnd_digits(r, 4)}", "phone")
    d.text(".\n\nSincerely,\nDr. " + r.choice(LAST) + "\n")
    return d.build()


def portal_message(r):
    d = Doc()
    first, last = r.choice(FIRST), r.choice(LAST)
    d.text("From: ")
    d.phi(f"{first} {last}", "name")
    d.text(" <")
    d.phi(f"{first.lower()}.{last.lower()}@outlook.com", "email")
    d.text(">\nSent: ")
    d.phi(f"{r.choice(MONTH_ABBR)} {r.randint(1, 28)}, {r.randint(2024, 2025)}", "date")
    d.text("\nSubject: Billing question\n\nHi, this is ")
    d.phi(f"{first} {last}", "name")
    d.text(". My new number is ")
    d.phi(f"({r.randint(201, 989)}) {r.randint(200, 999)}-{rnd_digits(r, 4)}", "phone")
    d.text(f". I was charged ${r.randint(25, 900)}.00 for visit #{rnd_digits(r, 6)}. Please use my card ")
    d.phi(" ".join(rnd_digits(r, 4) for _ in range(4)), "credit_card")
    d.text(". Subscriber ID ")
    d.phi(f"W{rnd_digits(r, 7)}", "member_id")
    d.text(".\nThanks!\n")
    return d.build()


def make_phi_holdout(r, n=120):
    builders = [discharge_summary, referral_letter, portal_message]
    rows = []
    for i in range(n):
        text, spans = builders[i % 3](r)
        rows.append({"id": f"hold-{i:03d}", "kind": builders[i % 3].__name__, "text": text, "spans": spans})
    return rows


POLICIES = [
    {"policy_id": "POL-001", "policy_name": "Standard Health Insurance Plan", "deductible": 1000, "annual_maximum": 50000,
     "coverage_rules": [{"treatment_type": "MRI", "coverage_percentage": 80, "requires_prior_authorization": True, "copay": 50},
                        {"treatment_type": "CT scan", "coverage_percentage": 80, "requires_prior_authorization": False, "copay": 50},
                        {"treatment_type": "X-ray", "coverage_percentage": 90, "requires_prior_authorization": False, "copay": 25},
                        {"treatment_type": "surgery", "coverage_percentage": 70, "requires_prior_authorization": True, "copay": 200},
                        {"treatment_type": "consultation", "coverage_percentage": 100, "requires_prior_authorization": False, "copay": 0}],
     "exclusions": ["cosmetic surgery", "acupuncture", "dental cleaning", "IVF"]},
    {"policy_id": "POL-002", "policy_name": "Premium Health Insurance Plan", "deductible": 500, "annual_maximum": 100000,
     "coverage_rules": [{"treatment_type": "MRI", "coverage_percentage": 90, "requires_prior_authorization": False, "copay": 25},
                        {"treatment_type": "CT scan", "coverage_percentage": 90, "requires_prior_authorization": False, "copay": 25},
                        {"treatment_type": "surgery", "coverage_percentage": 85, "requires_prior_authorization": True, "copay": 100},
                        {"treatment_type": "physical therapy", "coverage_percentage": 80, "requires_prior_authorization": False, "copay": 20}],
     "exclusions": ["cosmetic surgery", "experimental gene therapy"]},
    {"policy_id": "POL-003", "policy_name": "Bronze Essential Plan", "deductible": 6000, "annual_maximum": 25000,
     "coverage_rules": [{"treatment_type": "preventive visit", "coverage_percentage": 100, "requires_prior_authorization": False, "copay": 0},
                        {"treatment_type": "X-ray", "coverage_percentage": 60, "requires_prior_authorization": False, "copay": 40},
                        {"treatment_type": "emergency room visit", "coverage_percentage": 60, "requires_prior_authorization": False, "copay": 350}],
     "exclusions": ["MRI", "physical therapy", "chiropractic care", "cosmetic surgery"]},
    {"policy_id": "POL-004", "policy_name": "Dental and Vision Plus", "deductible": 50, "annual_maximum": 2000,
     "coverage_rules": [{"treatment_type": "dental cleaning", "coverage_percentage": 100, "requires_prior_authorization": False, "copay": 0},
                        {"treatment_type": "root canal", "coverage_percentage": 70, "requires_prior_authorization": False, "copay": 75},
                        {"treatment_type": "eye exam", "coverage_percentage": 100, "requires_prior_authorization": False, "copay": 10}],
     "exclusions": ["orthodontics for adults", "LASIK", "surgery", "MRI"]},
    {"policy_id": "POL-005", "policy_name": "Behavioral Health Plan", "deductible": 250, "annual_maximum": 15000,
     "coverage_rules": [{"treatment_type": "psychotherapy", "coverage_percentage": 90, "requires_prior_authorization": False, "copay": 15},
                        {"treatment_type": "psychiatric evaluation", "coverage_percentage": 90, "requires_prior_authorization": False, "copay": 15},
                        {"treatment_type": "inpatient psychiatric care", "coverage_percentage": 70, "requires_prior_authorization": True, "copay": 250}],
     "exclusions": ["marriage counseling", "life coaching", "MRI"]},
    {"policy_id": "POL-006", "policy_name": "Senior Advantage Plan", "deductible": 0, "annual_maximum": 75000,
     "coverage_rules": [{"treatment_type": "consultation", "coverage_percentage": 100, "requires_prior_authorization": False, "copay": 10},
                        {"treatment_type": "CT scan", "coverage_percentage": 85, "requires_prior_authorization": True, "copay": 40},
                        {"treatment_type": "hearing aids", "coverage_percentage": 50, "requires_prior_authorization": False, "copay": 0},
                        {"treatment_type": "cataract surgery", "coverage_percentage": 80, "requires_prior_authorization": True, "copay": 150}],
     "exclusions": ["cosmetic surgery", "IVF", "acupuncture"]},
]

TREATMENT_PHRASES = {
    "MRI": "MRI of the lumbar spine", "CT scan": "CT scan of the chest", "X-ray": "X-ray of the left wrist",
    "surgery": "laparoscopic gallbladder surgery", "consultation": "specialist consultation",
    "physical therapy": "12 sessions of physical therapy", "preventive visit": "annual preventive visit",
    "emergency room visit": "emergency room visit for a laceration", "dental cleaning": "routine dental cleaning",
    "root canal": "root canal on a molar", "eye exam": "comprehensive eye exam", "psychotherapy": "weekly psychotherapy",
    "psychiatric evaluation": "initial psychiatric evaluation", "inpatient psychiatric care": "5-day inpatient psychiatric care",
    "hearing aids": "bilateral hearing aids", "cataract surgery": "cataract surgery, right eye",
    "cosmetic surgery": "cosmetic rhinoplasty", "acupuncture": "acupuncture for chronic pain", "IVF": "one IVF cycle",
    "chiropractic care": "chiropractic spinal adjustment", "experimental gene therapy": "experimental gene therapy infusion",
    "orthodontics for adults": "adult orthodontic braces", "LASIK": "LASIK eye surgery",
    "marriage counseling": "marriage counseling sessions", "life coaching": "life coaching sessions",
}


def make_coverage(r):
    rows = []
    for p in POLICIES:
        for rule in p["coverage_rules"]:
            rows.append((p, rule["treatment_type"], True))
        for ex in p["exclusions"]:
            rows.append((p, ex, False))
    r.shuffle(rows)
    out = []
    for i, (p, treatment, covered) in enumerate(rows):
        out.append({
            "id": f"cov-{i:03d}",
            "policy_id": p["policy_id"],
            "plan_name": p["policy_name"],
            "treatment": TREATMENT_PHRASES[treatment],
            "treatment_type": treatment,
            "claim_amount": r.choice([180, 450, 1200, 2500, 6800, 14500]),
            "gold_covered": covered,
        })
    return out


def main():
    r = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    phi = make_phi(r)
    cov = make_coverage(r)
    holdout = make_phi_holdout(random.Random(SEED + 1))
    with open(OUT / "phi_holdout.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in holdout)
    with open(OUT / "phi_benchmark.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in phi)
    with open(OUT / "coverage_benchmark.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in cov)
    (OUT / "coverage_policies.json").write_text(json.dumps(POLICIES, indent=2))
    n_spans = sum(len(x["spans"]) for x in phi)
    print(f"phi_benchmark: {len(phi)} docs, {n_spans} gold PHI spans")
    print(f"phi_holdout: {len(holdout)} docs, {sum(len(x['spans']) for x in holdout)} gold PHI spans")
    print(f"coverage_benchmark: {len(cov)} cases ({sum(c['gold_covered'] for c in cov)} covered / "
          f"{sum(not c['gold_covered'] for c in cov)} not covered) across {len(POLICIES)} policies")


if __name__ == "__main__":
    main()
