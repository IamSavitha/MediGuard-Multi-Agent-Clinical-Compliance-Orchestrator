"""
Agent A: Triage Agent

Classifies incoming documents into categories:
- Medical Claim
- Patient Report
- Policy Update
- Other
"""

from typing import Dict, Any, Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from mediaguard.utils.llm_factory import get_llm
import json
import os
from dotenv import load_dotenv

load_dotenv()


class TriageAgent:
    """Agent responsible for classifying incoming medical documents."""
    
    DOCUMENT_TYPES = {
        "CLAIM": "Medical Claim",
        "PATIENT_REPORT": "Patient Report",
        "POLICY_UPDATE": "Policy Update",
        "OTHER": "Other Document"
    }
    
    def __init__(self, model_name: str = None):
        """Initialize the Triage Agent.
        
        Args:
            model_name: Model name to use (defaults from env vars)
        """
        self.model_name = model_name
        self.llm = get_llm(
            model_name=model_name,
            temperature=0.1,  # Low temperature for consistent classification
        )
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Set up the classification prompt template."""
        self.system_prompt = """You are a medical document classification specialist.
Your task is to analyze incoming documents and classify them into one of these categories:

1. CLAIM - Medical insurance claims, billing documents, treatment requests
2. PATIENT_REPORT - Clinical notes, patient records, medical histories
3. POLICY_UPDATE - Insurance policy changes, coverage updates, benefit modifications
4. OTHER - Any document that doesn't fit the above categories

Analyze the document carefully and respond with ONLY a JSON object in this format:
{
    "document_type": "CLAIM|PATIENT_REPORT|POLICY_UPDATE|OTHER",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification",
    "extracted_metadata": {
        "patient_id": "if present",
        "date": "if present",
        "treatment_type": "if present",
        "cost": "if present"
    }
}"""
        
        self.classification_prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "Classify this document:\n\n{document_text}")
        ])
    
    def classify(self, document_text: str) -> Dict[str, Any]:
        """Classify a document into one of the predefined categories.
        
        Args:
            document_text: The text content of the document to classify
            
        Returns:
            Dictionary containing classification results with:
            - document_type: The classified type
            - confidence: Confidence score (0-1)
            - reasoning: Explanation of classification
            - extracted_metadata: Any extracted metadata
        """
        try:
            # Get classification from LLM
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Classify this document:\n\n{document_text}")
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Try to extract JSON from response
            # Handle cases where response might have markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            classification = json.loads(response_text)
            
            # Validate document type
            if classification["document_type"] not in self.DOCUMENT_TYPES:
                classification["document_type"] = "OTHER"
                classification["confidence"] = 0.5
                classification["reasoning"] = "Unknown document type, defaulting to OTHER"
            
            return {
                "document_type": classification["document_type"],
                "document_type_label": self.DOCUMENT_TYPES[classification["document_type"]],
                "confidence": float(classification.get("confidence", 0.5)),
                "reasoning": classification.get("reasoning", ""),
                "extracted_metadata": classification.get("extracted_metadata", {}),
                "agent": "TriageAgent"
            }
            
        except json.JSONDecodeError as e:
            # Fallback classification if JSON parsing fails
            return {
                "document_type": "OTHER",
                "document_type_label": "Other Document",
                "confidence": 0.3,
                "reasoning": f"Failed to parse classification response: {str(e)}",
                "extracted_metadata": {},
                "agent": "TriageAgent",
                "error": str(e)
            }
        except Exception as e:
            return {
                "document_type": "OTHER",
                "document_type_label": "Other Document",
                "confidence": 0.0,
                "reasoning": f"Error during classification: {str(e)}",
                "extracted_metadata": {},
                "agent": "TriageAgent",
                "error": str(e)
            }
    
    def get_document_type_label(self, document_type: str) -> str:
        """Get human-readable label for a document type.
        
        Args:
            document_type: The document type code
            
        Returns:
            Human-readable label
        """
        return self.DOCUMENT_TYPES.get(document_type, "Unknown")
