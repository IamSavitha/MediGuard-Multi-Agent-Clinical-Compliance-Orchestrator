"""
Basic usage example for MediGuard.

This example demonstrates how to use the MediGuard orchestrator
to process a medical claim.
"""

from mediaguard import MediGuardOrchestrator
import json


def main():
    """Run basic usage example."""
    print("=" * 60)
    print("MediGuard - Basic Usage Example")
    print("=" * 60)
    
    # Initialize the orchestrator
    print("\n1. Initializing MediGuard Orchestrator...")
    orchestrator = MediGuardOrchestrator()
    print("   ✓ Orchestrator initialized")
    
    # Example claim text
    claim_text = """
    MEDICAL CLAIM
    
    Patient Information:
    Name: John Doe
    DOB: 01/15/1980
    Patient ID: PAT-12345
    Insurance: Standard Health Insurance Plan
    
    Treatment Details:
    Date of Service: 03/15/2024
    Provider: City Medical Center
    Treatment: MRI scan of brain
    Diagnosis: Headache evaluation
    
    Billing:
    Total Amount: $1,500.00
    """
    
    print("\n2. Processing medical claim...")
    print("   Claim: MRI scan of brain, $1,500.00")
    
    # Process the claim
    result = orchestrator.process_claim(claim_text)
    
    print("\n3. Results:")
    print(json.dumps(result, indent=2))
    
    # Display summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    if "classification" in result:
        classification = result["classification"]
        print(f"Document Type: {classification.get('document_type_label', 'N/A')}")
        print(f"Confidence: {classification.get('confidence', 0):.2%}")
    
    if "validation" in result and not result["validation"].get("skipped"):
        validation = result["validation"]
        print(f"\nCoverage Status: {'Covered' if validation.get('is_covered') else 'Not Covered'}")
        print(f"Coverage Percentage: {validation.get('coverage_percentage', 0)}%")
        print(f"Patient Co-pay: ${validation.get('copay_amount', 0):.2f}")
    
    if "compliance" in result:
        compliance = result["compliance"]
        phi_check = compliance.get("phi_check", {})
        print(f"\nPHI Detections: {phi_check.get('total_phi_detections', 0)}")
        print(f"Compliance Status: {'Compliant' if compliance.get('is_compliant') else 'Non-Compliant'}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
