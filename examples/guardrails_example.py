"""
Guardrails Example

This example demonstrates:
1. PHI detection and redaction
2. Bias detection in decisions
"""

from mediaguard.guardrails.phi_detector import PHIDetector
from mediaguard.guardrails.bias_detector import BiasDetector
from mediaguard.agents.compliance_auditor import ComplianceAuditor
import json


def main():
    """Run guardrails example."""
    print("=" * 60)
    print("MediGuard - Guardrails Example")
    print("=" * 60)
    
    # Example 1: PHI Detection
    print("\n1. PHI Detection Example")
    print("-" * 60)
    
    text_with_phi = """
    Patient: John Doe
    DOB: 01/15/1980
    SSN: 123-45-6789
    Phone: 555-123-4567
    Email: john.doe@email.com
    Medical Record Number: MRN: 987654321
    Account Number: Account: 123456789
    
    Treatment: MRI scan
    Amount: $1,500.00
    """
    
    print("Original text (contains PHI):")
    print(text_with_phi)
    
    phi_detector = PHIDetector()
    detected = phi_detector.detect_phi(text_with_phi)
    
    print(f"\nDetected PHI:")
    print(f"  Total detections: {detected['total_detections']}")
    for phi_type, items in detected.items():
        if phi_type != "total_detections" and isinstance(items, list) and items:
            print(f"  {phi_type}: {len(items)} instance(s)")
    
    # Redact PHI
    redacted_text, redaction_map = phi_detector.redact_phi(text_with_phi)
    
    print("\nRedacted text:")
    print(redacted_text)
    
    # Compliance check
    compliance = phi_detector.check_compliance(text_with_phi)
    print(f"\nCompliance Status:")
    print(f"  Compliant: {compliance['is_compliant']}")
    print(f"  Risk Level: {compliance['risk_level']}")
    print(f"  Recommendation: {compliance['recommendation']}")
    
    # Example 2: Bias Detection
    print("\n\n2. Bias Detection Example")
    print("-" * 60)
    
    # Example decision that might have bias
    decision = {
        "is_covered": False,
        "coverage_percentage": 0,
        "treatment_type": "experimental therapy",
        "reasoning": "Treatment is experimental and not covered under standard plan",
        "copay_amount": 0
    }
    
    patient_metadata = {
        "age": 72,
        "insurance_type": "Medicaid",
        "income_level": "low"
    }
    
    print("Decision to analyze:")
    print(json.dumps(decision, indent=2))
    
    print("\nPatient metadata:")
    print(json.dumps(patient_metadata, indent=2))
    
    bias_detector = BiasDetector()
    bias_result = bias_detector.detect_bias(
        decision=decision,
        context="Coverage decision for experimental treatment",
        patient_metadata=patient_metadata
    )
    
    print("\nBias Detection Results:")
    print(f"  Has Bias: {bias_result.get('has_bias', False)}")
    print(f"  Bias Types: {bias_result.get('bias_types', [])}")
    print(f"  Severity: {bias_result.get('bias_severity', 'N/A')}")
    print(f"  Evidence: {bias_result.get('evidence', 'N/A')}")
    print(f"  Recommendations:")
    for rec in bias_result.get('recommendations', []):
        print(f"    - {rec}")
    
    # Example 3: Full Compliance Audit
    print("\n\n3. Full Compliance Audit Example")
    print("-" * 60)
    
    output_text = f"""
    Classification: Medical Claim
    Validation: {json.dumps(decision, indent=2)}
    Patient: John Doe, DOB: 01/15/1980, SSN: 123-45-6789
    """
    
    auditor = ComplianceAuditor()
    audit_result = auditor.audit(
        output_text=output_text,
        decision=decision,
        patient_metadata=patient_metadata
    )
    
    print("Audit Results:")
    print(f"  Compliant: {audit_result.get('is_compliant', False)}")
    print(f"  Risk Level: {audit_result.get('risk_level', 'N/A')}")
    print(f"  Recommendations:")
    for rec in audit_result.get('recommendations', []):
        print(f"    - {rec}")
    
    if audit_result.get('phi_check', {}).get('redacted_text'):
        print("\n  Redacted Output:")
        print(audit_result['phi_check']['redacted_text'])
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
