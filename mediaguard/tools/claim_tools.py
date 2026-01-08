"""
Tool-Use Functions for Claim Processing

These functions can be called by LLM agents to perform calculations
and validations during claim processing.
"""

from typing import Dict, Any, Optional
import re
from datetime import datetime


def calculate_copay(claim_amount: float, coverage_percentage: float) -> float:
    """Calculate the patient's co-pay amount.
    
    Args:
        claim_amount: Total claim amount
        coverage_percentage: Percentage covered by insurance (0-100)
        
    Returns:
        Co-pay amount the patient must pay
    """
    if coverage_percentage < 0 or coverage_percentage > 100:
        raise ValueError("Coverage percentage must be between 0 and 100")
    
    covered_amount = claim_amount * (coverage_percentage / 100)
    copay = claim_amount - covered_amount
    return round(copay, 2)


def check_deductible(claim_amount: float, deductible_remaining: float) -> bool:
    """Check if deductible applies to this claim.
    
    Args:
        claim_amount: Amount of the claim
        deductible_remaining: Remaining deductible amount
        
    Returns:
        True if deductible applies, False otherwise
    """
    return deductible_remaining > 0 and claim_amount > 0


def calculate_coverage_amount(
    claim_amount: float,
    coverage_percentage: float,
    deductible_remaining: float = 0
) -> Dict[str, Any]:
    """Calculate detailed coverage breakdown.
    
    Args:
        claim_amount: Total claim amount
        coverage_percentage: Percentage covered by insurance
        deductible_remaining: Remaining deductible amount
        
    Returns:
        Dictionary with coverage breakdown
    """
    # Apply deductible first
    if deductible_remaining > 0:
        amount_after_deductible = max(0, claim_amount - deductible_remaining)
    else:
        amount_after_deductible = claim_amount
    
    # Calculate coverage
    covered_amount = amount_after_deductible * (coverage_percentage / 100)
    patient_responsibility = claim_amount - covered_amount
    
    return {
        "total_claim": round(claim_amount, 2),
        "deductible_applied": round(min(claim_amount, deductible_remaining), 2),
        "amount_after_deductible": round(amount_after_deductible, 2),
        "covered_amount": round(covered_amount, 2),
        "patient_responsibility": round(patient_responsibility, 2),
        "coverage_percentage": coverage_percentage
    }


def validate_claim_format(claim_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the format and required fields of a claim.
    
    Args:
        claim_data: Dictionary containing claim information
        
    Returns:
        Dictionary with validation results
    """
    required_fields = ["patient_id", "treatment", "amount", "date"]
    missing_fields = []
    invalid_fields = []
    
    # Check required fields
    for field in required_fields:
        if field not in claim_data:
            missing_fields.append(field)
    
    # Validate amount
    if "amount" in claim_data:
        try:
            amount = float(claim_data["amount"])
            if amount < 0:
                invalid_fields.append("amount (must be positive)")
        except (ValueError, TypeError):
            invalid_fields.append("amount (must be a number)")
    
    # Validate date
    if "date" in claim_data:
        date_str = claim_data["date"]
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            try:
                datetime.strptime(date_str, "%m/%d/%Y")
            except (ValueError, TypeError):
                invalid_fields.append("date (must be in YYYY-MM-DD or MM/DD/YYYY format)")
    
    is_valid = len(missing_fields) == 0 and len(invalid_fields) == 0
    
    return {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "message": "Valid" if is_valid else "Validation failed"
    }


def extract_claim_info(text: str) -> Dict[str, Any]:
    """Extract claim information from unstructured text.
    
    Args:
        text: Unstructured text containing claim information
        
    Returns:
        Dictionary with extracted claim information
    """
    extracted = {}
    
    # Extract amounts (currency)
    amount_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    amounts = re.findall(amount_pattern, text)
    if amounts:
        # Take the largest amount as likely claim amount
        amounts_float = [float(a.replace(',', '')) for a in amounts]
        extracted["amount"] = max(amounts_float)
    
    # Extract dates
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
    ]
    for pattern in date_patterns:
        dates = re.findall(pattern, text)
        if dates:
            extracted["date"] = dates[0]
            break
    
    # Extract treatment types (common medical terms)
    treatment_keywords = [
        "MRI", "CT scan", "X-ray", "surgery", "procedure", "treatment",
        "therapy", "medication", "prescription", "consultation"
    ]
    for keyword in treatment_keywords:
        if keyword.lower() in text.lower():
            extracted["treatment_type"] = keyword
            break
    
    return extracted
