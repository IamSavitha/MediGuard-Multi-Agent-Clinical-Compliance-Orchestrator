"""
PHI (Personal Health Information) Detector and Redactor

Detects and redacts PHI from documents to ensure HIPAA compliance.

Rule-based detection of HIPAA Safe Harbor identifiers: names, dates, phone numbers, email
addresses, SSNs, medical record / account / member numbers, payment card numbers and street
addresses with ZIP codes. Numbers that belong to providers or claims (NPI, claim, tax ID, ...)
are filtered out by context. Measured accuracy is in evaluation/RESULTS.md.
"""

import re
from typing import Dict, List, Any, Tuple

_MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|"
          r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
_STREET_SUFFIX = (r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|"
                  r"Place|Pl|Terrace|Ter|Circle|Cir|Parkway|Pkwy|Highway|Hwy)")
_CAP_WORD = r"[A-Z][a-z]+(?:['-][A-Z]?[a-z]+)?"


class PHIDetector:
    """Detects and redacts PHI from text documents."""

    # Whole-match patterns: (output type, regex, flags)
    PATTERNS = [
        ("ssn", r"\b\d{3}-\d{2}-\d{4}\b", 0),
        ("ssn", r"\b\d{9}\b", 0),  # undashed; context-filtered below
        ("phone", r"(?<![\d-])(?:\+1[\s.-]?)?(?:\(\d{3}\)\s?\d{3}[-.\s]?\d{4}|\d{3}[-.\s]\d{3}[-.\s]\d{4}|\d{10})(?![\d-])", 0),
        ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0),
        ("dates", r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b", 0),
        ("dates", r"\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b", 0),
        ("dates", rf"\b{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+(?:19|20)\d{{2}}\b", re.IGNORECASE),
        ("credit_card", r"\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b", 0),
        ("address", rf"\b\d{{1,5}}\s+(?:{_CAP_WORD}\.?\s+){{1,3}}{_STREET_SUFFIX}\b\.?", 0),
    ]

    # Label-anchored patterns: only capture group 1 is PHI.
    LABELED_PATTERNS = [
        ("medical_record_number", r"\b(?i:MRN|Medical\s+Record(?:\s+(?:Number|No\.?|#))?)\s*[:#-]?\s*(\d{5,12})\b"),
        ("account_number", r"\b(?i:Account(?:\s+(?:Number|No\.?|#))?|Acct\.?)\s*[:#-]?\s*(\d{6,})\b"),
        ("member_id", r"\b(?i:(?:Member|Subscriber|Beneficiary|Insurance|Policy\s*holder|Patient)\s*(?:ID|No\.?|Number|#))"
                      r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{4,}\d)\b"),
        ("address", r"\b[A-Z]{2}\s+(\d{5}(?:-\d{4})?)\b"),  # ZIP after a state code
    ]

    # Patterns whose group 1 is a person's name.
    NAME_PATTERNS = [
        # "Patient: John Doe", "Patient Name: ...", "Name: ...", "Re: ...", "From: ..."
        rf"\b(?i:Patient(?:\s+Name)?|Name|Re|From|Insured|Member\s+Name|Subscriber\s+Name)[ \t]*:[ \t]*({_CAP_WORD}(?:[ \t]+{_CAP_WORD})+)\b",
        # JSON-like: "patient_name": "Jane Smith"
        rf"(?i:patient_id|patient_name|full_name|name|patient)[\"']?\s*[:=]\s*[\"']({_CAP_WORD}(?:[ \t]+{_CAP_WORD})+)[\"']",
        # Free text lead-ins: "my patient, Jane Smith", "this is Jane Smith", "my name is Jane Smith"
        rf"\b(?i:patient,?|this\s+is|my\s+name\s+is)\s+({_CAP_WORD}[ \t]+{_CAP_WORD})\b",
    ]
    # Honorifics for patients (provider titles such as "Dr." are not patient PHI).
    HONORIFIC_PATTERN = rf"\b(?:Mr|Mrs|Ms|Miss|Mx)\.?[ \t]+({_CAP_WORD}(?:[ \t]+{_CAP_WORD})?)\b"

    # Digits preceded by these labels identify providers, claims or orders, not the patient.
    NON_PATIENT_CONTEXT = re.compile(
        r"(?i)(?:\bNPI|\bclaim(?:[ _]?(?:id|no|number|#))?|\btax\s*id|\bTIN|\bEIN|\bgroup(?:\s*(?:no|number|#))?|"
        r"\bpolicy(?:\s*(?:no|number|#))?|\bprior\s+auth\w*(?:\s+ref)?|\bref(?:erence)?|\bvisit|\border|\binvoice|"
        r"\bconfirmation|\bCPT|\bICD(?:-10)?|\bDRG|\broom)\W{0,4}$"
    )
    NUMERIC_TYPES = {"ssn", "phone"}

    def __init__(self):
        """Initialize the PHI detector."""
        self.detected_phi = []
        self.redaction_map = {}

    def _non_patient_number(self, text: str, start: int) -> bool:
        return bool(self.NON_PATIENT_CONTEXT.search(text[max(0, start - 24):start]))

    def detect_phi(self, text: str) -> Dict[str, Any]:
        """Detect all PHI in the text.

        Args:
            text: Text to scan for PHI

        Returns:
            Dictionary containing detected PHI (lists of {value, start, end}) and total_detections
        """
        detected = {
            "ssn": [],
            "phone": [],
            "email": [],
            "dates": [],
            "medical_record_number": [],
            "account_number": [],
            "member_id": [],
            "credit_card": [],
            "address": [],
            "names": [],
            "total_detections": 0
        }
        taken = []  # spans already claimed, so one string is not reported under two types

        def add(kind, start, end):
            if any(start < e and s < end for s, e in taken):
                return
            taken.append((start, end))
            detected[kind].append({"value": text[start:end], "start": start, "end": end})
            detected["total_detections"] += 1

        # Label-anchored identifiers first: they are the most specific.
        for kind, pattern in self.LABELED_PATTERNS:
            for m in re.finditer(pattern, text):
                add(kind, m.start(1), m.end(1))

        for kind, pattern, flags in self.PATTERNS:
            for m in re.finditer(pattern, text, flags):
                if kind in self.NUMERIC_TYPES and self._non_patient_number(text, m.start()):
                    continue
                add(kind, m.start(), m.end())

        # Names: find them via labels / lead-ins / honorifics, then redact every occurrence.
        full_names, surnames = set(), set()
        for pattern in self.NAME_PATTERNS:
            for m in re.finditer(pattern, text):
                name = " ".join(m.group(1).split())
                if "\n" not in m.group(1):
                    full_names.add(name)
                    surnames.add(name.split()[-1])
        for m in re.finditer(self.HONORIFIC_PATTERN, text):
            full_names.add(" ".join(m.group(0).split()))
        for name in sorted(full_names, key=len, reverse=True):
            for m in re.finditer(r"\b" + r"\s+".join(map(re.escape, name.split())) + r"\b", text):
                add("names", m.start(), m.end())
        for surname in surnames:  # "Mr. Alvarez" after "Patient: Carlos Alvarez"
            for m in re.finditer(rf"\b(?:Mr|Mrs|Ms|Miss|Mx)\.?[ \t]+{re.escape(surname)}\b", text):
                add("names", m.start(), m.end())

        self.detected_phi = detected
        return detected

    def redact_phi(self, text: str, replacement: str = "[REDACTED]") -> Tuple[str, Dict[str, Any]]:
        """Redact all detected PHI from text.
        
        Args:
            text: Text to redact
            replacement: String to replace PHI with
            
        Returns:
            Tuple of (redacted_text, redaction_map)
        """
        # First detect all PHI
        detected = self.detect_phi(text)
        
        # Create a list of all redaction positions
        redactions = []
        
        for phi_type, items in detected.items():
            if phi_type == "total_detections" or not isinstance(items, list):
                continue
            for item in items:
                redactions.append({
                    "type": phi_type,
                    "start": item["start"],
                    "end": item["end"],
                    "original": item["value"]
                })
        
        # Merge overlapping redactions to avoid double redaction
        if redactions:
            # Sort by start position
            redactions.sort(key=lambda x: x["start"])
            merged = []
            for redaction in redactions:
                if not merged:
                    merged.append(redaction)
                else:
                    last = merged[-1]
                    # Check if overlapping or adjacent
                    if redaction["start"] <= last["end"]:
                        # Merge: extend the last redaction to cover both
                        merged[-1] = {
                            "type": last["type"],  # Keep first type
                            "start": last["start"],
                            "end": max(last["end"], redaction["end"]),
                            "original": last["original"]  # Keep first original
                        }
                    else:
                        merged.append(redaction)
            redactions = merged
        
        # Sort by start position (descending) to redact from end to start
        redactions.sort(key=lambda x: x["start"], reverse=True)
        
        # Apply redactions
        redacted_text = text
        redaction_map = {}
        
        for redaction in redactions:
            start = redaction["start"]
            end = redaction["end"]
            original = redaction["original"]
            phi_type = redaction["type"]
            
            # Store mapping
            if phi_type not in redaction_map:
                redaction_map[phi_type] = []
            redaction_map[phi_type].append(original)
            
            # Replace in text
            redacted_text = (
                redacted_text[:start] +
                replacement +
                redacted_text[end:]
            )
        
        self.redaction_map = redaction_map
        return redacted_text, redaction_map
    
    def check_compliance(self, text: str) -> Dict[str, Any]:
        """Check if text contains PHI and assess compliance risk.
        
        Args:
            text: Text to check
            
        Returns:
            Compliance assessment dictionary
        """
        detected = self.detect_phi(text)
        total = detected["total_detections"]
        
        # Risk assessment
        risk_level = "LOW"
        if total > 10:
            risk_level = "HIGH"
        elif total > 5:
            risk_level = "MEDIUM"
        elif total > 0:
            risk_level = "LOW"
        
        # Critical PHI types
        critical_types = ["ssn", "credit_card", "medical_record_number", "member_id"]
        has_critical = any(
            len(detected.get(phi_type, [])) > 0
            for phi_type in critical_types
        )
        
        if has_critical:
            risk_level = "HIGH"
        
        return {
            "is_compliant": total == 0,
            "risk_level": risk_level,
            "total_phi_detections": total,
            "detected_types": {
                k: len(v) if isinstance(v, list) else 0
                for k, v in detected.items()
                if k != "total_detections"
            },
            "has_critical_phi": has_critical,
            "recommendation": (
                "No PHI detected. Safe to proceed."
                if total == 0
                else f"Detected {total} PHI instances. Redaction recommended."
            )
        }
    
    def get_redaction_summary(self) -> Dict[str, Any]:
        """Get summary of redactions performed.
        
        Returns:
            Summary dictionary
        """
        total_redactions = sum(
            len(items) for items in self.redaction_map.values()
        )
        
        return {
            "total_redactions": total_redactions,
            "redaction_by_type": {
                phi_type: len(items)
                for phi_type, items in self.redaction_map.items()
            },
            "redaction_map": self.redaction_map
        }
