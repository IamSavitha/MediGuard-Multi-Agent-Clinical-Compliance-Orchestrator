"""Load insurance policy JSON files into a VectorStore."""
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DEFAULT_POLICY_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_policies"


def policy_to_text(policy: Dict[str, Any]) -> str:
    """Render a policy as the text that gets embedded and shown to the validator."""
    exclusions = policy.get("exclusions") or []
    return f"""
Policy: {policy['policy_name']}
Policy ID: {policy['policy_id']}

Coverage Rules:
{json.dumps(policy['coverage_rules'], indent=2)}

Exclusions (not covered): {', '.join(exclusions) if exclusions else 'none listed'}

Deductible: ${policy['deductible']}
Annual Maximum: ${policy['annual_maximum']}
Effective Date: {policy.get('effective_date', 'N/A')}
Expiration Date: {policy.get('expiration_date', 'N/A')}
"""


def policy_metadata(policy: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "policy_name": policy["policy_name"],
        "deductible": policy["deductible"],
        "annual_maximum": policy["annual_maximum"],
        "effective_date": policy.get("effective_date") or "",
        "expiration_date": policy.get("expiration_date") or "",
    }


def load_policies(vector_store, policies: Iterable[Dict[str, Any]]) -> int:
    """Add policies to the store. Returns how many were loaded."""
    n = 0
    for policy in policies:
        vector_store.add_policy(policy["policy_id"], policy_to_text(policy), policy_metadata(policy))
        n += 1
    return n


def load_policy_dir(vector_store, directory: Optional[Path] = None) -> int:
    """Load every *.json policy in a directory (defaults to data/sample_policies)."""
    directory = Path(directory or DEFAULT_POLICY_DIR)
    policies = [json.loads(p.read_text()) for p in sorted(directory.glob("*.json"))]
    return load_policies(vector_store, policies)
