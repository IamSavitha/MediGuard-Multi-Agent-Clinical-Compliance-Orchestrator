"""
Setup script to load sample policies into the vector database.

Run this script to populate the vector database with sample policies.
"""

from mediaguard.rag.vector_store import VectorStore
import json
from pathlib import Path


def load_policy_file(file_path: str) -> dict:
    """Load a policy JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def main():
    """Load sample policies into vector database."""
    print("Setting up MediGuard policies...")
    print("=" * 60)
    
    # Initialize vector store
    vector_store = VectorStore()
    
    # Load policies from data directory
    data_dir = Path(__file__).parent / "data" / "sample_policies"
    
    if not data_dir.exists():
        print(f"Error: Policies directory not found: {data_dir}")
        return
    
    policies_loaded = 0
    
    for policy_file in data_dir.glob("*.json"):
        try:
            policy = load_policy_file(str(policy_file))
            
            # Convert policy to text for embedding
            policy_text = f"""
Policy: {policy['policy_name']}
Policy ID: {policy['policy_id']}

Coverage Rules:
{json.dumps(policy['coverage_rules'], indent=2)}

Deductible: ${policy['deductible']}
Annual Maximum: ${policy['annual_maximum']}
Effective Date: {policy.get('effective_date', 'N/A')}
Expiration Date: {policy.get('expiration_date', 'N/A')}
"""
            
            # Add to vector store
            vector_store.add_policy(
                policy_id=policy['policy_id'],
                policy_text=policy_text,
                metadata={
                    "policy_name": policy['policy_name'],
                    "deductible": policy['deductible'],
                    "annual_maximum": policy['annual_maximum'],
                    "effective_date": policy.get('effective_date'),
                    "expiration_date": policy.get('expiration_date')
                }
            )
            
            policies_loaded += 1
            print(f"✓ Loaded: {policy['policy_name']} ({policy['policy_id']})")
            
        except Exception as e:
            print(f"✗ Error loading {policy_file}: {e}")
    
    print("=" * 60)
    print(f"Total policies loaded: {policies_loaded}")
    print("\nPolicies are now available for RAG-based policy validation.")


if __name__ == "__main__":
    main()
