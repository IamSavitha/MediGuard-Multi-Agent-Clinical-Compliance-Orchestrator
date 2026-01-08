"""
Agent B: Policy Validator

Uses RAG (Retrieval-Augmented Generation) to query insurance policies
and validate if treatments are covered.
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from mediaguard.rag.vector_store import VectorStore
from mediaguard.tools.claim_tools import calculate_copay, check_deductible
import json
import os
from dotenv import load_dotenv

load_dotenv()


class PolicyValidator:
    """Agent responsible for validating treatments against insurance policies using RAG."""
    
    def __init__(self, model_name: str = None, vector_store: VectorStore = None):
        """Initialize the Policy Validator Agent.
        
        Args:
            model_name: OpenAI model to use (defaults to gpt-4o)
            vector_store: Vector store instance for policy retrieval
        """
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.2,  # Low temperature for accurate policy interpretation
        )
        self.vector_store = vector_store or VectorStore()
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Set up the validation prompt template."""
        self.system_prompt = """You are an expert insurance policy validator specializing in medical claim coverage.
Your task is to:
1. Analyze treatment requests against insurance policy documents
2. Determine if the treatment is covered
3. Calculate coverage details (co-pay, deductible, coverage percentage)
4. Provide clear reasoning for your decisions

You have access to:
- Relevant policy documents retrieved from the knowledge base
- Tool functions for calculating co-pays and checking deductibles

Always base your decisions on the actual policy documents provided, not assumptions.
If information is unclear, indicate uncertainty rather than guessing.

Respond with a JSON object containing:
{
    "is_covered": true/false,
    "coverage_percentage": 0-100,
    "copay_amount": number,
    "deductible_applies": true/false,
    "reasoning": "Detailed explanation",
    "policy_references": ["policy IDs that were relevant"],
    "confidence": 0.0-1.0
}"""
    
    def validate_treatment(
        self,
        treatment_description: str,
        patient_metadata: Dict[str, Any] = None,
        claim_amount: float = None
    ) -> Dict[str, Any]:
        """Validate a treatment against insurance policies.
        
        Args:
            treatment_description: Description of the treatment/procedure
            patient_metadata: Patient information (insurance plan, etc.)
            claim_amount: Amount of the claim
            
        Returns:
            Dictionary containing validation results
        """
        try:
            # Step 1: Retrieve relevant policies using RAG
            relevant_policies = self._retrieve_relevant_policies(treatment_description)
            
            # Step 2: Build context from retrieved policies
            policy_context = self._build_policy_context(relevant_policies)
            
            # Step 3: Use LLM to analyze coverage
            validation_result = self._analyze_coverage(
                treatment_description,
                policy_context,
                patient_metadata,
                claim_amount
            )
            
            # Step 4: Use tools to calculate financial details
            if validation_result.get("is_covered", False):
                validation_result = self._apply_financial_tools(
                    validation_result,
                    claim_amount,
                    patient_metadata
                )
            
            validation_result["agent"] = "PolicyValidator"
            validation_result["policies_consulted"] = len(relevant_policies)
            
            return validation_result
            
        except Exception as e:
            return {
                "is_covered": False,
                "coverage_percentage": 0,
                "copay_amount": 0,
                "deductible_applies": False,
                "reasoning": f"Error during validation: {str(e)}",
                "policy_references": [],
                "confidence": 0.0,
                "agent": "PolicyValidator",
                "error": str(e)
            }
    
    def _retrieve_relevant_policies(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant policies using vector search.
        
        Args:
            query: Search query
            top_k: Number of policies to retrieve
            
        Returns:
            List of relevant policy documents
        """
        results = self.vector_store.search_similar(query, top_k=top_k)
        return results
    
    def _build_policy_context(self, policies: List[Dict[str, Any]]) -> str:
        """Build a context string from retrieved policies.
        
        Args:
            policies: List of policy search results
            
        Returns:
            Formatted context string
        """
        if not policies:
            return "No relevant policies found in the knowledge base."
        
        context_parts = ["Relevant Policy Documents:"]
        for i, policy in enumerate(policies, 1):
            policy_id = policy.get("id", f"Policy_{i}")
            score = policy.get("score", 0.0)
            metadata = policy.get("metadata", {})
            text = policy.get("text", "")
            
            context_parts.append(f"\n--- Policy {i} (ID: {policy_id}, Relevance: {score:.2f}) ---")
            if text:
                context_parts.append(text[:1000])  # Limit text length
            elif metadata:
                context_parts.append(f"Metadata: {json.dumps(metadata, indent=2)}")
        
        return "\n".join(context_parts)
    
    def _analyze_coverage(
        self,
        treatment_description: str,
        policy_context: str,
        patient_metadata: Dict[str, Any] = None,
        claim_amount: float = None
    ) -> Dict[str, Any]:
        """Use LLM to analyze coverage based on policies.
        
        Args:
            treatment_description: Description of treatment
            policy_context: Context from retrieved policies
            patient_metadata: Patient information
            claim_amount: Claim amount
            
        Returns:
            Validation result dictionary
        """
        patient_info = ""
        if patient_metadata:
            patient_info = f"\nPatient Information: {json.dumps(patient_metadata, indent=2)}"
        
        claim_info = ""
        if claim_amount:
            claim_info = f"\nClaim Amount: ${claim_amount:,.2f}"
        
        prompt = f"""{self.system_prompt}

{policy_context}

Treatment to Validate:
{treatment_description}
{patient_info}
{claim_info}

Analyze whether this treatment is covered and provide your validation result."""
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        response_text = response.content.strip()
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                "is_covered": False,
                "coverage_percentage": 0,
                "copay_amount": 0,
                "deductible_applies": False,
                "reasoning": "Could not parse validation response",
                "policy_references": [],
                "confidence": 0.3
            }
    
    def _apply_financial_tools(
        self,
        validation_result: Dict[str, Any],
        claim_amount: float = None,
        patient_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Apply financial calculation tools.
        
        Args:
            validation_result: Current validation result
            claim_amount: Claim amount
            patient_metadata: Patient information
            
        Returns:
            Updated validation result with financial calculations
        """
        if not claim_amount:
            return validation_result
        
        # Use tool to calculate co-pay
        coverage_pct = validation_result.get("coverage_percentage", 80)
        copay = calculate_copay(claim_amount, coverage_pct)
        validation_result["copay_amount"] = copay
        
        # Check deductible if patient metadata available
        if patient_metadata:
            deductible_remaining = patient_metadata.get("deductible_remaining", 0)
            validation_result["deductible_applies"] = check_deductible(
                claim_amount,
                deductible_remaining
            )
        
        return validation_result
