"""
Bias Detector

Detects potential bias patterns in AI decision-making, particularly
in healthcare coverage decisions.
"""

from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from mediaguard.utils.llm_factory import get_llm
import json
import os
from dotenv import load_dotenv

load_dotenv()


class BiasDetector:
    """Detects bias patterns in AI-generated decisions and outputs."""
    
    # Known bias patterns to check
    BIAS_PATTERNS = {
        "demographic": [
            "age", "gender", "race", "ethnicity", "religion",
            "sexual orientation", "disability status"
        ],
        "socioeconomic": [
            "income", "education", "employment status", "insurance type"
        ],
        "geographic": [
            "location", "zip code", "rural", "urban"
        ],
        "treatment": [
            "experimental", "alternative", "pre-existing condition"
        ]
    }
    
    def __init__(self, model_name: str = None):
        """Initialize the Bias Detector.
        
        Args:
            model_name: Model name to use (defaults from env vars)
        """
        self.model_name = model_name
        self.llm = get_llm(
            model_name=model_name,
            temperature=0.1,  # Low temperature for consistent analysis
        )
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Set up the bias detection prompt."""
        self.system_prompt = """You are an expert in detecting bias in AI decision-making, particularly in healthcare and insurance contexts.

Your task is to analyze decisions and outputs for potential bias patterns including:
1. Demographic bias (age, gender, race, ethnicity, etc.)
2. Socioeconomic bias (income, education, insurance type)
3. Geographic bias (location-based discrimination)
4. Treatment bias (unfair treatment of certain conditions or procedures)
5. Algorithmic bias (systematic errors in decision-making)

Analyze the provided decision and context, then respond with a JSON object:
{
    "has_bias": true/false,
    "bias_types": ["list of detected bias types"],
    "bias_severity": "LOW|MEDIUM|HIGH",
    "affected_groups": ["groups potentially affected"],
    "evidence": "Specific evidence of bias",
    "recommendations": ["recommendations to mitigate bias"],
    "confidence": 0.0-1.0
}

Be thorough but fair - only flag actual bias, not legitimate medical or policy distinctions."""
    
    def detect_bias(
        self,
        decision: Dict[str, Any],
        context: Optional[str] = None,
        patient_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Detect bias in a decision or output.
        
        Args:
            decision: The decision/output to analyze
            context: Additional context about the decision
            patient_metadata: Patient information (if available)
            
        Returns:
            Dictionary containing bias detection results
        """
        try:
            # Build analysis prompt
            decision_str = json.dumps(decision, indent=2)
            
            prompt_parts = [
                "Analyze this decision for potential bias:",
                f"\nDecision:\n{decision_str}"
            ]
            
            if context:
                prompt_parts.append(f"\nContext:\n{context}")
            
            if patient_metadata:
                prompt_parts.append(f"\nPatient Metadata:\n{json.dumps(patient_metadata, indent=2)}")
            
            prompt = "\n".join(prompt_parts)
            
            # Get bias analysis from LLM
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
            
            bias_result = json.loads(response_text)
            
            # Also perform pattern-based checks
            pattern_checks = self._pattern_based_checks(decision, patient_metadata)
            
            # Combine results
            if pattern_checks.get("has_bias", False):
                if not bias_result.get("has_bias", False):
                    bias_result["has_bias"] = True
                    bias_result["bias_types"] = pattern_checks.get("bias_types", [])
                    bias_result["bias_severity"] = "MEDIUM"
                    bias_result["evidence"] = pattern_checks.get("evidence", "")
            
            bias_result["agent"] = "BiasDetector"
            return bias_result
            
        except json.JSONDecodeError as e:
            return {
                "has_bias": False,
                "bias_types": [],
                "bias_severity": "UNKNOWN",
                "affected_groups": [],
                "evidence": f"Error parsing bias analysis: {str(e)}",
                "recommendations": ["Review decision manually"],
                "confidence": 0.0,
                "agent": "BiasDetector",
                "error": str(e)
            }
        except Exception as e:
            return {
                "has_bias": False,
                "bias_types": [],
                "bias_severity": "UNKNOWN",
                "affected_groups": [],
                "evidence": f"Error during bias detection: {str(e)}",
                "recommendations": ["Review decision manually"],
                "confidence": 0.0,
                "agent": "BiasDetector",
                "error": str(e)
            }
    
    def _pattern_based_checks(
        self,
        decision: Dict[str, Any],
        patient_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform pattern-based bias checks.
        
        Args:
            decision: Decision to check
            patient_metadata: Patient information
            
        Returns:
            Pattern-based bias detection results
        """
        detected_bias = []
        evidence = []
        
        # Check if decision is consistently negative for certain groups
        if patient_metadata:
            # Check for demographic-based patterns
            if "age" in patient_metadata:
                age = patient_metadata.get("age", 0)
                if age > 65 and decision.get("is_covered", False) == False:
                    # Could indicate age bias, but need more context
                    pass
            
            # Check insurance type bias
            insurance_type = patient_metadata.get("insurance_type", "").lower()
            if "medicaid" in insurance_type or "medicare" in insurance_type:
                if decision.get("coverage_percentage", 0) < 50:
                    detected_bias.append("socioeconomic")
                    evidence.append("Lower coverage percentage for public insurance")
        
        # Check for treatment type bias
        treatment = decision.get("treatment_type", "").lower()
        experimental_keywords = ["experimental", "alternative", "investigational"]
        if any(keyword in treatment for keyword in experimental_keywords):
            if decision.get("is_covered", False) == False:
                # This might be legitimate, but worth flagging
                detected_bias.append("treatment")
                evidence.append("Experimental treatment denied - verify policy")
        
        return {
            "has_bias": len(detected_bias) > 0,
            "bias_types": detected_bias,
            "evidence": "; ".join(evidence) if evidence else ""
        }
    
    def check_decision_fairness(
        self,
        decisions: List[Dict[str, Any]],
        group_key: str = "insurance_type"
    ) -> Dict[str, Any]:
        """Check fairness across multiple decisions grouped by a key.
        
        Args:
            decisions: List of decisions to analyze
            group_key: Key to group decisions by
            
        Returns:
            Fairness analysis results
        """
        if not decisions:
            return {
                "is_fair": True,
                "groups_analyzed": 0,
                "fairness_metrics": {},
                "recommendations": []
            }
        
        # Group decisions
        groups = {}
        for decision in decisions:
            group = decision.get(group_key, "unknown")
            if group not in groups:
                groups[group] = []
            groups[group].append(decision)
        
        # Calculate metrics per group
        fairness_metrics = {}
        for group, group_decisions in groups.items():
            total = len(group_decisions)
            covered = sum(1 for d in group_decisions if d.get("is_covered", False))
            avg_coverage = sum(
                d.get("coverage_percentage", 0) for d in group_decisions
            ) / total if total > 0 else 0
            
            fairness_metrics[group] = {
                "total_decisions": total,
                "coverage_rate": covered / total if total > 0 else 0,
                "avg_coverage_percentage": avg_coverage
            }
        
        # Check for significant disparities
        coverage_rates = [
            metrics["coverage_rate"]
            for metrics in fairness_metrics.values()
        ]
        
        if len(coverage_rates) > 1:
            max_rate = max(coverage_rates)
            min_rate = min(coverage_rates)
            disparity = max_rate - min_rate
            
            is_fair = disparity < 0.15  # Less than 15% difference
        else:
            is_fair = True
            disparity = 0
        
        return {
            "is_fair": is_fair,
            "groups_analyzed": len(groups),
            "fairness_metrics": fairness_metrics,
            "disparity": disparity,
            "recommendations": (
                ["Fairness check passed"]
                if is_fair
                else [f"Significant disparity detected: {disparity:.2%} difference in coverage rates"]
            )
        }
