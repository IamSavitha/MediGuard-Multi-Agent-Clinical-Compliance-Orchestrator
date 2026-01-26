"""
Pipeline Router

Routes documents to appropriate pipelines based on risk assessment:
- LOW_RISK: Standard processing pipeline
- HIGH_RISK: Enhanced validation pipeline
- CRITICAL_PHI: Specialized PHI handling pipeline
- QUARANTINE: Bad records requiring human review
"""

from typing import Dict, Any, Optional, Literal, List
from enum import Enum
from datetime import datetime
import json
from pathlib import Path


class PipelineType(str, Enum):
    """Pipeline types for routing."""
    LOW_RISK = "low_risk"
    HIGH_RISK = "high_risk"
    CRITICAL_PHI = "critical_phi"
    QUARANTINE = "quarantine"
    HUMAN_REVIEW = "human_review"


class RiskLevel(str, Enum):
    """Risk levels for documents."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PipelineRouter:
    """Routes documents to appropriate pipelines based on risk assessment."""
    
    def __init__(self, quarantine_dir: Optional[str] = None):
        """Initialize the pipeline router.
        
        Args:
            quarantine_dir: Directory for storing quarantined records
        """
        self.quarantine_dir = Path(quarantine_dir) if quarantine_dir else Path("data/quarantine")
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # Risk thresholds
        self.phi_critical_threshold = 5  # Critical if 5+ PHI detections
        self.bias_high_threshold = "MEDIUM"  # High risk if bias severity >= MEDIUM
        self.error_threshold = 3  # Quarantine if 3+ errors
    
    def assess_risk(
        self,
        audit_result: Dict[str, Any],
        classification_result: Optional[Dict[str, Any]] = None,
        validation_result: Optional[Dict[str, Any]] = None,
        errors: Optional[list] = None
    ) -> Dict[str, Any]:
        """Assess overall risk level for a document.
        
        Args:
            audit_result: Compliance audit results
            classification_result: Document classification results
            validation_result: Policy validation results
            errors: List of processing errors
            
        Returns:
            Risk assessment dictionary
        """
        risk_factors = []
        risk_score = 0
        risk_level = RiskLevel.LOW
        
        # Check PHI detections
        phi_check = audit_result.get("phi_check", {})
        phi_count = phi_check.get("total_phi_detections", 0)
        phi_risk_level = phi_check.get("risk_level", "LOW")
        
        if phi_count >= self.phi_critical_threshold:
            risk_factors.append(f"Critical PHI: {phi_count} detections")
            risk_score += 10
            risk_level = RiskLevel.CRITICAL
        elif phi_count > 0:
            risk_factors.append(f"PHI detected: {phi_count} instances")
            risk_score += phi_count * 2
        
        if phi_risk_level == "HIGH":
            risk_score += 5
            if risk_level != RiskLevel.CRITICAL:
                risk_level = RiskLevel.HIGH
        
        # Check bias
        bias_check = audit_result.get("bias_check", {})
        if bias_check.get("has_bias", False):
            bias_severity = bias_check.get("bias_severity", "LOW")
            risk_factors.append(f"Bias detected: {bias_severity} severity")
            
            if bias_severity == "HIGH":
                risk_score += 8
                if risk_level != RiskLevel.CRITICAL:
                    risk_level = RiskLevel.HIGH
            elif bias_severity == "MEDIUM":
                risk_score += 4
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.MEDIUM
        
        # Check compliance
        if not audit_result.get("is_compliant", True):
            risk_factors.append("Non-compliant")
            risk_score += 3
        
        # Check errors
        error_count = len(errors) if errors else 0
        if error_count >= self.error_threshold:
            risk_factors.append(f"Multiple errors: {error_count}")
            risk_score += error_count * 2
            risk_level = RiskLevel.CRITICAL
        
        # Check validation confidence
        if validation_result:
            confidence = validation_result.get("confidence", 1.0)
            if confidence < 0.5:
                risk_factors.append(f"Low validation confidence: {confidence:.2%}")
                risk_score += 2
        
        # Determine final risk level based on score
        if risk_score >= 15:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 10:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 5:
            risk_level = RiskLevel.MEDIUM
        
        return {
            "risk_level": risk_level.value,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "phi_count": phi_count,
            "has_bias": bias_check.get("has_bias", False),
            "is_compliant": audit_result.get("is_compliant", True),
            "error_count": error_count,
            "timestamp": datetime.now().isoformat()
        }
    
    def route(
        self,
        document_id: str,
        document_text: str,
        audit_result: Dict[str, Any],
        classification_result: Optional[Dict[str, Any]] = None,
        validation_result: Optional[Dict[str, Any]] = None,
        errors: Optional[list] = None,
        full_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Route document to appropriate pipeline.
        
        Args:
            document_id: Unique document identifier
            document_text: Original document text
            audit_result: Compliance audit results
            classification_result: Document classification results
            validation_result: Policy validation results
            errors: List of processing errors
            full_result: Complete processing result
            
        Returns:
            Routing decision dictionary
        """
        # Assess risk
        risk_assessment = self.assess_risk(
            audit_result=audit_result,
            classification_result=classification_result,
            validation_result=validation_result,
            errors=errors
        )
        
        risk_level = risk_assessment["risk_level"]
        phi_count = risk_assessment["phi_count"]
        error_count = risk_assessment["error_count"]
        
        # Determine pipeline
        pipeline = None
        requires_human_review = False
        quarantine_reason = None
        
        # Quarantine: Bad records (errors, malformed data)
        if error_count >= self.error_threshold or not audit_result.get("is_compliant", True):
            pipeline = PipelineType.QUARANTINE
            quarantine_reason = f"Processing errors: {error_count} errors" if error_count >= self.error_threshold else "Non-compliant"
            requires_human_review = True
        
        # Critical PHI: High PHI count or critical risk
        elif risk_level == RiskLevel.CRITICAL or phi_count >= self.phi_critical_threshold:
            pipeline = PipelineType.CRITICAL_PHI
            requires_human_review = True  # Always require human review for critical PHI
        
        # High Risk: Bias, medium-high PHI, or high risk level
        elif risk_level == RiskLevel.HIGH or risk_assessment.get("has_bias", False):
            pipeline = PipelineType.HIGH_RISK
            if risk_level == RiskLevel.HIGH:
                requires_human_review = True
        
        # Low Risk: Standard processing
        else:
            pipeline = PipelineType.LOW_RISK
        
        routing_decision = {
            "document_id": document_id,
            "pipeline": pipeline.value,
            "risk_assessment": risk_assessment,
            "requires_human_review": requires_human_review,
            "quarantine_reason": quarantine_reason,
            "timestamp": datetime.now().isoformat(),
            "routing_metadata": {
                "phi_count": phi_count,
                "error_count": error_count,
                "risk_level": risk_level,
                "is_compliant": audit_result.get("is_compliant", True)
            }
        }
        
        # If quarantined, save to quarantine directory
        if pipeline == PipelineType.QUARANTINE:
            self._quarantine_record(document_id, document_text, routing_decision, full_result)
        
        return routing_decision
    
    def _quarantine_record(
        self,
        document_id: str,
        document_text: str,
        routing_decision: Dict[str, Any],
        full_result: Optional[Dict[str, Any]]
    ):
        """Save record to quarantine directory.
        
        Args:
            document_id: Document identifier
            document_text: Original document text
            routing_decision: Routing decision details
            full_result: Complete processing result
        """
        quarantine_record = {
            "document_id": document_id,
            "document_text": document_text,
            "routing_decision": routing_decision,
            "full_result": full_result,
            "quarantined_at": datetime.now().isoformat()
        }
        
        quarantine_file = self.quarantine_dir / f"{document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(quarantine_file, "w") as f:
            json.dump(quarantine_record, f, indent=2)
    
    def get_quarantine_records(self) -> List[Dict[str, Any]]:
        """Get all quarantined records.
        
        Returns:
            List of quarantine record dictionaries
        """
        records = []
        for file_path in self.quarantine_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    records.append(json.load(f))
            except Exception as e:
                # Log error but continue
                continue
        return records
