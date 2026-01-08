"""
Agent C: Compliance & Ethics Auditor

Scans outputs for PHI leaks and checks for bias in decision-making.
"""

from typing import Dict, Any, Optional, Tuple
from mediaguard.guardrails.phi_detector import PHIDetector
from mediaguard.guardrails.bias_detector import BiasDetector


class ComplianceAuditor:
    """Agent responsible for compliance auditing (PHI detection and bias checking)."""
    
    def __init__(self):
        """Initialize the Compliance Auditor Agent."""
        self.phi_detector = PHIDetector()
        self.bias_detector = BiasDetector()
    
    def audit(
        self,
        output_text: str,
        decision: Optional[Dict[str, Any]] = None,
        patient_metadata: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive compliance audit.
        
        Args:
            output_text: Text output to audit
            decision: Decision/output dictionary to check for bias
            patient_metadata: Patient information (for bias context)
            context: Additional context for bias detection
            
        Returns:
            Dictionary containing audit results
        """
        audit_results = {
            "phi_check": {},
            "bias_check": {},
            "is_compliant": True,
            "risk_level": "LOW",
            "recommendations": []
        }
        
        # Step 1: PHI Detection and Redaction
        phi_compliance = self.phi_detector.check_compliance(output_text)
        audit_results["phi_check"] = phi_compliance
        
        if not phi_compliance["is_compliant"]:
            # Redact PHI
            redacted_text, redaction_map = self.phi_detector.redact_phi(output_text)
            audit_results["phi_check"]["redacted_text"] = redacted_text
            audit_results["phi_check"]["redaction_map"] = redaction_map
            audit_results["is_compliant"] = False
            audit_results["risk_level"] = phi_compliance["risk_level"]
            audit_results["recommendations"].append(
                f"PHI detected: {phi_compliance['total_phi_detections']} instances. "
                "Text has been redacted."
            )
        
        # Step 2: Bias Detection
        if decision:
            bias_result = self.bias_detector.detect_bias(
                decision=decision,
                context=context,
                patient_metadata=patient_metadata
            )
            audit_results["bias_check"] = bias_result
            
            if bias_result.get("has_bias", False):
                audit_results["is_compliant"] = False
                severity = bias_result.get("bias_severity", "LOW")
                
                # Update risk level
                if severity == "HIGH":
                    audit_results["risk_level"] = "HIGH"
                elif severity == "MEDIUM" and audit_results["risk_level"] == "LOW":
                    audit_results["risk_level"] = "MEDIUM"
                
                audit_results["recommendations"].extend(
                    bias_result.get("recommendations", [])
                )
        
        # Final compliance status
        if audit_results["is_compliant"]:
            audit_results["recommendations"].append(
                "All compliance checks passed. Output is safe to use."
            )
        
        audit_results["agent"] = "ComplianceAuditor"
        return audit_results
    
    def redact_phi(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Redact PHI from text.
        
        Args:
            text: Text to redact
            
        Returns:
            Tuple of (redacted_text, redaction_map)
        """
        return self.phi_detector.redact_phi(text)
    
    def check_bias(
        self,
        decision: Dict[str, Any],
        patient_metadata: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check for bias in a decision.
        
        Args:
            decision: Decision to check
            patient_metadata: Patient information
            context: Additional context
            
        Returns:
            Bias detection results
        """
        return self.bias_detector.detect_bias(
            decision=decision,
            context=context,
            patient_metadata=patient_metadata
        )
