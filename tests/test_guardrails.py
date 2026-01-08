"""Tests for guardrails modules."""

import pytest
from mediaguard.guardrails.phi_detector import PHIDetector
from mediaguard.guardrails.bias_detector import BiasDetector


def test_phi_detector_ssn():
    """Test SSN detection."""
    detector = PHIDetector()
    text = "SSN: 123-45-6789"
    
    detected = detector.detect_phi(text)
    assert detected["total_detections"] > 0
    assert len(detected["ssn"]) > 0


def test_phi_detector_redaction():
    """Test PHI redaction."""
    detector = PHIDetector()
    text = "Patient: John Doe, SSN: 123-45-6789, Phone: 555-123-4567"
    
    redacted, redaction_map = detector.redact_phi(text)
    
    assert "[REDACTED]" in redacted
    assert "123-45-6789" not in redacted
    assert len(redaction_map) > 0


def test_phi_detector_compliance():
    """Test compliance checking."""
    detector = PHIDetector()
    text = "No PHI here, just regular text"
    
    compliance = detector.check_compliance(text)
    assert compliance["is_compliant"] is True
    assert compliance["total_phi_detections"] == 0


def test_bias_detector():
    """Test bias detection."""
    detector = BiasDetector()
    
    decision = {
        "is_covered": True,
        "coverage_percentage": 80
    }
    
    result = detector.detect_bias(decision)
    assert "has_bias" in result
    assert "bias_severity" in result


if __name__ == "__main__":
    pytest.main([__file__])
