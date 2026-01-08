"""Tests for MediGuard agents."""

import pytest
from mediaguard.agents.triage_agent import TriageAgent
from mediaguard.agents.compliance_auditor import ComplianceAuditor


def test_triage_agent_classification():
    """Test document classification by TriageAgent."""
    agent = TriageAgent()
    
    # Test claim classification
    claim_text = "Medical claim for MRI scan, amount $1,500"
    result = agent.classify(claim_text)
    
    assert "document_type" in result
    assert "confidence" in result
    assert result["document_type"] in ["CLAIM", "PATIENT_REPORT", "POLICY_UPDATE", "OTHER"]


def test_compliance_auditor_phi_detection():
    """Test PHI detection by ComplianceAuditor."""
    auditor = ComplianceAuditor()
    
    text_with_phi = "Patient: John Doe, DOB: 01/15/1980, SSN: 123-45-6789"
    result = auditor.audit(text_with_phi)
    
    assert "phi_check" in result
    assert "is_compliant" in result
    # Should detect PHI in this text
    assert result["phi_check"]["total_phi_detections"] > 0


def test_compliance_auditor_bias_detection():
    """Test bias detection by ComplianceAuditor."""
    auditor = ComplianceAuditor()
    
    decision = {
        "is_covered": False,
        "coverage_percentage": 0,
        "treatment_type": "experimental therapy"
    }
    
    result = auditor.check_bias(decision)
    
    assert "has_bias" in result
    assert "bias_severity" in result


if __name__ == "__main__":
    pytest.main([__file__])
