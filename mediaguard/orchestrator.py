"""
MediGuard Orchestrator

Main orchestration system using LangGraph to coordinate all agents.
"""

from typing import Dict, Any, Optional, TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from mediaguard.agents.triage_agent import TriageAgent
from mediaguard.agents.policy_validator import PolicyValidator
from mediaguard.agents.compliance_auditor import ComplianceAuditor
from mediaguard.rag.vector_store import VectorStore
from mediaguard.pipeline.router import PipelineRouter, PipelineType
from mediaguard.pipeline.handlers import (
    LowRiskPipelineHandler,
    HighRiskPipelineHandler,
    CriticalPHIPipelineHandler
)
from mediaguard.pipeline.human_loop import HumanInTheLoopQueue
from mediaguard.pipeline.quarantine import QuarantineManager
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


class MediGuardState(TypedDict):
    """State structure for the MediGuard workflow."""
    document_text: str
    document_id: Optional[str]
    document_type: Optional[str]
    classification_result: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    audit_result: Optional[Dict[str, Any]]
    patient_metadata: Optional[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]
    routing_decision: Optional[Dict[str, Any]]
    errors: Annotated[list[str], add_messages]
    messages: Annotated[list, add_messages]


class MediGuardOrchestrator:
    """Main orchestrator for the MediGuard multi-agent system."""
    
    def __init__(
        self,
        model_name: str = None,
        vector_store: VectorStore = None,
        enable_guardrails: bool = True,
        enable_pipeline_routing: bool = True
    ):
        """Initialize the MediGuard Orchestrator.
        
        Args:
            model_name: OpenAI model to use
            vector_store: Vector store instance for RAG
            enable_guardrails: Whether to enable compliance auditing
            enable_pipeline_routing: Whether to enable pipeline routing
        """
        self.model_name = model_name
        self.vector_store = vector_store
        self.enable_guardrails = enable_guardrails
        self.enable_pipeline_routing = enable_pipeline_routing
        
        # Initialize agents
        self.triage_agent = TriageAgent(model_name=model_name)
        self.policy_validator = PolicyValidator(
            model_name=model_name,
            vector_store=vector_store or VectorStore()
        )
        self.compliance_auditor = ComplianceAuditor() if enable_guardrails else None
        
        # Initialize pipeline components
        if enable_pipeline_routing:
            self.pipeline_router = PipelineRouter()
            self.quarantine_manager = QuarantineManager()
            self.human_loop_queue = HumanInTheLoopQueue()
            self.low_risk_handler = LowRiskPipelineHandler(self)
            self.high_risk_handler = HighRiskPipelineHandler(self)
            self.critical_phi_handler = CriticalPHIPipelineHandler(self)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow.
        
        Returns:
            Compiled StateGraph workflow
        """
        workflow = StateGraph(MediGuardState)
        
        # Add nodes
        workflow.add_node("triage", self._triage_node)
        workflow.add_node("validate", self._validate_node)
        
        if self.enable_guardrails:
            workflow.add_node("audit", self._audit_node)
        
        if self.enable_pipeline_routing:
            workflow.add_node("route", self._route_node)
        
        # Add edges
        workflow.set_entry_point("triage")
        workflow.add_edge("triage", "validate")
        
        if self.enable_guardrails:
            workflow.add_edge("validate", "audit")
            if self.enable_pipeline_routing:
                workflow.add_edge("audit", "route")
                workflow.add_edge("route", END)
            else:
                workflow.add_edge("audit", END)
        else:
            if self.enable_pipeline_routing:
                workflow.add_edge("validate", "route")
                workflow.add_edge("route", END)
            else:
                workflow.add_edge("validate", END)
        
        return workflow.compile()
    
    def _triage_node(self, state: MediGuardState) -> MediGuardState:
        """Triage node: Classify the document.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with classification results
        """
        try:
            document_text = state.get("document_text", "")
            classification_result = self.triage_agent.classify(document_text)
            
            state["classification_result"] = classification_result
            state["document_type"] = classification_result.get("document_type")
            
            # Extract patient metadata if available
            if "extracted_metadata" in classification_result:
                state["patient_metadata"] = classification_result["extracted_metadata"]
            
            return state
            
        except Exception as e:
            state["errors"] = state.get("errors", []) + [f"Triage error: {str(e)}"]
            state["classification_result"] = {
                "document_type": "OTHER",
                "error": str(e)
            }
            return state
    
    def _validate_node(self, state: MediGuardState) -> MediGuardState:
        """Validation node: Validate against policies.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with validation results
        """
        try:
            document_text = state.get("document_text", "")
            document_type = state.get("document_type", "OTHER")
            patient_metadata = state.get("patient_metadata", {})
            
            # Only validate claims
            if document_type != "CLAIM":
                state["validation_result"] = {
                    "skipped": True,
                    "reason": f"Document type {document_type} does not require policy validation"
                }
                return state
            
            # Extract treatment and amount from document
            treatment_info = self._extract_treatment_info(document_text, patient_metadata)
            
            # Validate treatment
            validation_result = self.policy_validator.validate_treatment(
                treatment_description=treatment_info.get("treatment", document_text),
                patient_metadata=patient_metadata,
                claim_amount=treatment_info.get("amount")
            )
            
            state["validation_result"] = validation_result
            return state
            
        except Exception as e:
            state["errors"] = state.get("errors", []) + [f"Validation error: {str(e)}"]
            state["validation_result"] = {
                "is_covered": False,
                "error": str(e)
            }
            return state
    
    def _audit_node(self, state: MediGuardState) -> MediGuardState:
        """Audit node: Compliance and bias checking.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with audit results
        """
        if not self.compliance_auditor:
            return state
        
        try:
            document_text = state.get("document_text", "")
            validation_result = state.get("validation_result", {})
            patient_metadata = state.get("patient_metadata", {})
            
            # Build output text for PHI checking
            output_text = self._build_output_text(state)
            
            # Combine original document text with output text for comprehensive PHI checking
            # This ensures we catch PHI in both the original input and the processed output
            text_to_check = f"{document_text}\n\n{output_text}"
            
            # Perform audit
            audit_result = self.compliance_auditor.audit(
                output_text=text_to_check,
                decision=validation_result,
                patient_metadata=patient_metadata,
                context=f"Document type: {state.get('document_type')}"
            )
            
            state["audit_result"] = audit_result
            
            # If PHI was detected, update final output with redacted text
            if audit_result.get("phi_check", {}).get("redacted_text"):
                state["final_output"] = self._build_final_output(state, redacted=True)
            else:
                state["final_output"] = self._build_final_output(state)
            
            return state
            
        except Exception as e:
            state["errors"] = state.get("errors", []) + [f"Audit error: {str(e)}"]
            state["audit_result"] = {
                "is_compliant": False,
                "error": str(e)
            }
            return state
    
    def _route_node(self, state: MediGuardState) -> MediGuardState:
        """Route node: Determine pipeline and route document.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with routing decision
        """
        if not self.enable_pipeline_routing:
            return state
        
        try:
            document_id = state.get("document_id", f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            document_text = state.get("document_text", "")
            audit_result = state.get("audit_result", {})
            classification_result = state.get("classification_result")
            validation_result = state.get("validation_result")
            errors = state.get("errors", [])
            final_output = state.get("final_output")
            
            # Route document
            routing_decision = self.pipeline_router.route(
                document_id=document_id,
                document_text=document_text,
                audit_result=audit_result,
                classification_result=classification_result,
                validation_result=validation_result,
                errors=errors,
                full_result=final_output
            )
            
            state["routing_decision"] = routing_decision
            
            # Add routing info to final output
            if final_output:
                final_output["routing"] = routing_decision
            
            # If requires human review, add to queue
            if routing_decision.get("requires_human_review", False):
                priority = "critical" if routing_decision["risk_assessment"]["risk_level"] == "CRITICAL" else "high"
                self.human_loop_queue.add_to_queue(
                    document_id=document_id,
                    document_text=document_text,
                    reason=routing_decision.get("quarantine_reason") or "High risk document",
                    processing_result=final_output or {},
                    priority=priority
                )
            
            return state
            
        except Exception as e:
            state["errors"] = state.get("errors", []) + [f"Routing error: {str(e)}"]
            return state
    
    def _extract_treatment_info(
        self,
        document_text: str,
        patient_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract treatment information from document text.
        
        Args:
            document_text: Document text
            patient_metadata: Patient metadata
            
        Returns:
            Dictionary with treatment information
        """
        import re
        
        info = {}
        
        # Extract amount
        amount_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        amounts = re.findall(amount_pattern, document_text)
        if amounts:
            amounts_float = [float(a.replace(',', '')) for a in amounts]
            info["amount"] = max(amounts_float)
        
        # Extract treatment keywords
        treatment_keywords = [
            "MRI", "CT scan", "X-ray", "surgery", "procedure", "treatment",
            "therapy", "medication", "prescription", "consultation", "lab test"
        ]
        for keyword in treatment_keywords:
            if keyword.lower() in document_text.lower():
                info["treatment"] = keyword
                break
        
        if "treatment" not in info:
            # Try to extract sentence with "treatment" or "procedure"
            sentences = document_text.split('.')
            for sentence in sentences:
                if any(word in sentence.lower() for word in ["treatment", "procedure", "service"]):
                    info["treatment"] = sentence.strip()
                    break
        
        return info
    
    def _build_output_text(self, state: MediGuardState) -> str:
        """Build output text for PHI checking.
        
        Args:
            state: Current workflow state
            
        Returns:
            Output text string
        """
        parts = []
        
        if state.get("classification_result"):
            parts.append(f"Classification: {json.dumps(state['classification_result'], indent=2)}")
        
        if state.get("validation_result"):
            parts.append(f"Validation: {json.dumps(state['validation_result'], indent=2)}")
        
        if state.get("patient_metadata"):
            parts.append(f"Patient Info: {json.dumps(state['patient_metadata'], indent=2)}")
        
        return "\n".join(parts)
    
    def _build_final_output(
        self,
        state: MediGuardState,
        redacted: bool = False
    ) -> Dict[str, Any]:
        """Build the final output dictionary.
        
        Args:
            state: Current workflow state
            redacted: Whether to use redacted text
            
        Returns:
            Final output dictionary
        """
        output = {
            "timestamp": datetime.now().isoformat(),
            "document_type": state.get("document_type"),
            "classification": state.get("classification_result"),
            "validation": state.get("validation_result"),
            "compliance": state.get("audit_result"),
            "status": "completed"
        }
        
        if redacted and state.get("audit_result", {}).get("phi_check", {}).get("redacted_text"):
            output["redacted_output"] = state["audit_result"]["phi_check"]["redacted_text"]
        
        if state.get("errors"):
            output["errors"] = state["errors"]
            output["status"] = "completed_with_errors"
        
        return output
    
    def process_document(
        self,
        document_text: str,
        document_type: Optional[str] = None,
        patient_metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a document through the full workflow.
        
        Args:
            document_text: Text content of the document
            document_type: Optional pre-classified document type
            patient_metadata: Optional patient metadata
            document_id: Optional document identifier
            
        Returns:
            Final output dictionary with all results
        """
        # Initialize state
        initial_state: MediGuardState = {
            "document_text": document_text,
            "document_id": document_id or f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "document_type": document_type,
            "classification_result": None,
            "validation_result": None,
            "audit_result": None,
            "patient_metadata": patient_metadata or {},
            "final_output": None,
            "routing_decision": None,
            "errors": [],
            "messages": []
        }
        
        # Run the workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            return final_state.get("final_output", final_state)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def process_claim(
        self,
        claim_text: str,
        patient_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a medical claim specifically.
        
        Args:
            claim_text: Text content of the claim
            patient_metadata: Patient information
            
        Returns:
            Claim processing results
        """
        return self.process_document(
            document_text=claim_text,
            document_type="CLAIM",
            patient_metadata=patient_metadata
        )
    
    def process_batch(
        self,
        documents: List[Dict[str, Any]],
        max_workers: int = 4,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """Process multiple documents in batch.
        
        Args:
            documents: List of document dictionaries, each containing:
                - 'id' (str): Unique identifier for the document
                - 'text' (str): Document text content
                - 'document_type' (str, optional): Pre-classified document type
                - 'patient_metadata' (dict, optional): Patient information
            max_workers: Maximum number of parallel workers (default: 4)
            show_progress: Whether to show progress bar (default: True)
            
        Returns:
            Dictionary containing:
                - 'results': List of processing results (one per document)
                - 'summary': Summary statistics
                - 'errors': List of documents that failed processing
        """
        results = []
        errors = []
        total = len(documents)
        
        def process_single(doc: Dict[str, Any]) -> Dict[str, Any]:
            """Process a single document."""
            doc_id = doc.get('id', f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
            try:
                result = self.process_document(
                    document_text=doc.get('text', ''),
                    document_type=doc.get('document_type'),
                    patient_metadata=doc.get('patient_metadata'),
                    document_id=doc_id
                )
                result['document_id'] = doc_id
                return result
            except Exception as e:
                return {
                    'document_id': doc_id,
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        # Process documents in parallel
        if show_progress:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_doc = {
                    executor.submit(process_single, doc): doc 
                    for doc in documents
                }
                
                with tqdm(total=total, desc="Processing documents") as pbar:
                    for future in as_completed(future_to_doc):
                        result = future.result()
                        if result.get('status') == 'error':
                            errors.append(result)
                        else:
                            results.append(result)
                        pbar.update(1)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_doc = {
                    executor.submit(process_single, doc): doc 
                    for doc in documents
                }
                
                for future in as_completed(future_to_doc):
                    result = future.result()
                    if result.get('status') == 'error':
                        errors.append(result)
                    else:
                        results.append(result)
        
        # Calculate summary statistics
        summary = {
            'total': total,
            'successful': len(results),
            'failed': len(errors),
            'success_rate': len(results) / total if total > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'results': results,
            'summary': summary,
            'errors': errors
        }
