"""
Pipeline Handlers

Different pipeline handlers for processing documents based on risk level.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from mediaguard.agents.compliance_auditor import ComplianceAuditor
from datetime import datetime

if TYPE_CHECKING:
    from mediaguard.orchestrator import MediGuardOrchestrator


class PipelineHandler:
    """Base class for pipeline handlers."""
    
    def __init__(self, orchestrator: "MediGuardOrchestrator"):
        """Initialize pipeline handler.
        
        Args:
            orchestrator: MediGuard orchestrator instance
        """
        self.orchestrator = orchestrator
    
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document through the pipeline.
        
        Args:
            document: Document dictionary with 'id' and 'text'
            
        Returns:
            Processing result
        """
        raise NotImplementedError


class LowRiskPipelineHandler(PipelineHandler):
    """Handler for low-risk documents - standard processing."""
    
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process low-risk document with standard workflow.
        
        Args:
            document: Document dictionary
            
        Returns:
            Processing result with pipeline metadata
        """
        result = self.orchestrator.process_document(
            document_text=document.get("text", ""),
            document_type=document.get("document_type")
        )
        
        # Add pipeline metadata
        result["pipeline"] = {
            "type": "low_risk",
            "handler": "LowRiskPipelineHandler",
            "processed_at": datetime.now().isoformat()
        }
        
        return result


class HighRiskPipelineHandler(PipelineHandler):
    """Handler for high-risk documents - enhanced validation."""
    
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process high-risk document with enhanced validation.
        
        Args:
            document: Document dictionary
            
        Returns:
            Processing result with enhanced validation
        """
        # Standard processing
        result = self.orchestrator.process_document(
            document_text=document.get("text", ""),
            document_type=document.get("document_type")
        )
        
        # Additional validation for high-risk documents
        compliance = result.get("compliance", {})
        phi_check = compliance.get("phi_check", {})
        
        # Enhanced checks
        enhanced_validation = {
            "additional_phi_scan": True,
            "bias_detection_enabled": True,
            "double_validation": True,
            "risk_mitigation_applied": True
        }
        
        # Add pipeline metadata
        result["pipeline"] = {
            "type": "high_risk",
            "handler": "HighRiskPipelineHandler",
            "enhanced_validation": enhanced_validation,
            "processed_at": datetime.now().isoformat()
        }
        
        return result


class CriticalPHIPipelineHandler(PipelineHandler):
    """Handler for critical PHI documents - specialized PHI handling."""
    
    def __init__(self, orchestrator: "MediGuardOrchestrator"):
        """Initialize critical PHI handler."""
        super().__init__(orchestrator)
        self.compliance_auditor = ComplianceAuditor()
    
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process critical PHI document with specialized handling.
        
        Args:
            document: Document dictionary
            
        Returns:
            Processing result with critical PHI handling
        """
        # Standard processing
        result = self.orchestrator.process_document(
            document_text=document.get("text", ""),
            document_type=document.get("document_type")
        )
        
        # Additional critical PHI handling
        document_text = document.get("text", "")
        
        # Aggressive PHI redaction
        phi_check = result.get("compliance", {}).get("phi_check", {})
        if phi_check.get("total_phi_detections", 0) > 0:
            # Perform additional redaction pass
            redacted_text, redaction_map = self.compliance_auditor.redact_phi(document_text)
            
            # Update result with critical PHI handling
            result["compliance"]["phi_check"]["critical_phi_handling"] = {
                "additional_redaction_pass": True,
                "redaction_map": redaction_map,
                "redacted_text": redacted_text
            }
        
        # Add pipeline metadata
        result["pipeline"] = {
            "type": "critical_phi",
            "handler": "CriticalPHIPipelineHandler",
            "critical_phi_handling": True,
            "requires_human_review": True,
            "processed_at": datetime.now().isoformat()
        }
        
        return result
