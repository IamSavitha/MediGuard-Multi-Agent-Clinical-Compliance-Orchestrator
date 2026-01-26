"""
PHI (Personal Health Information) Detector and Redactor

Detects and redacts PHI from documents to ensure HIPAA compliance.
"""

import re
from typing import Dict, List, Any, Tuple


class PHIDetector:
    """Detects and redacts PHI from text documents."""
    
    # Common PHI patterns
    PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "ssn_no_dash": r"\b\d{9}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "date_of_birth": r"\b(0[1-9]|1[0-2])[/-](0[1-9]|[12][0-9]|3[01])[/-]\d{4}\b",
        "medical_record_number": r"\bMRN[:\s]?\d{6,}\b",
        "account_number": r"\bAccount[:\s]?\d{6,}\b",
        "credit_card": r"\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b",
    }
    
    # Common name patterns (basic - can be enhanced with NER)
    # Patterns to detect patient names in various formats
    NAME_PATTERNS = [
        # Pattern 1: "Patient: John Doe" or "Name: Jane Smith"
        r"\b(?:Patient|Name|DOB|Date of Birth)[: \t]+([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)+)\b",
        # Pattern 2: JSON-like format "patient_id": "John Doe" or "patient_name": "Jane Smith"
        r"(?:patient_id|patient_name|name|patient)[\"\']?\s*[:=]\s*[\"\']?([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)+)[\"\']?",
    ]
    
    def __init__(self):
        """Initialize the PHI detector."""
        self.detected_phi = []
        self.redaction_map = {}
    
    def detect_phi(self, text: str) -> Dict[str, Any]:
        """Detect all PHI in the text.
        
        Args:
            text: Text to scan for PHI
            
        Returns:
            Dictionary containing detected PHI and statistics
        """
        detected = {
            "ssn": [],
            "phone": [],
            "email": [],
            "date_of_birth": [],
            "medical_record_number": [],
            "account_number": [],
            "credit_card": [],
            "names": [],
            "total_detections": 0
        }
        
        # Map pattern types to detected dict keys
        # "ssn_no_dash" should map to "ssn"
        type_mapping = {
            "ssn": "ssn",
            "ssn_no_dash": "ssn",  # Fix: map ssn_no_dash to ssn
            "phone": "phone",
            "email": "email",
            "date_of_birth": "date_of_birth",
            "medical_record_number": "medical_record_number",
            "account_number": "account_number",
            "credit_card": "credit_card",
        }
        
        # Detect structured PHI
        for phi_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Use mapped type for detected dict
                mapped_type = type_mapping.get(phi_type, phi_type)
                detected[mapped_type].append({
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })
                detected["total_detections"] += 1
        
        # Detect names (basic pattern matching)
        # Track unique names to avoid double counting (normalized for comparison)
        unique_names = set()
        for pattern in self.NAME_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) > 0:
                    name = match.group(1).strip()
                    # Reject names with newlines or other invalid characters
                    if '\n' in name or '\r' in name:
                        continue
                    # Basic validation: names should be 2+ words, capitalized, no newlines
                    name_parts = name.split()
                    if len(name_parts) >= 2 and name[0].isupper() and all(part[0].isupper() for part in name_parts if part):
                        # Normalize name for uniqueness check (case-insensitive, normalized whitespace)
                        normalized_name = ' '.join(name_parts).strip()
                        # Always add to detected list for redaction (redact all instances)
                        detected["names"].append({
                            "value": normalized_name,
                            "start": match.start(1),
                            "end": match.end(1)
                        })
                        # Only count unique name values to avoid double counting (case-insensitive)
                        name_key = normalized_name.lower()
                        if name_key not in unique_names:
                            unique_names.add(name_key)
                            detected["total_detections"] += 1
        
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
        critical_types = ["ssn", "credit_card", "medical_record_number"]
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
