"""
RAG (Retrieval-Augmented Generation) Example

This example demonstrates how to:
1. Add policies to the vector database
2. Search for relevant policies
3. Use RAG for policy validation
"""

from mediaguard.rag.vector_store import VectorStore
from mediaguard.agents.policy_validator import PolicyValidator
import json
from pathlib import Path


def load_policy_file(file_path: str) -> dict:
    """Load a policy JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def main():
    """Run RAG example."""
    print("=" * 60)
    print("MediGuard - RAG Example")
    print("=" * 60)
    
    # Initialize vector store
    print("\n1. Initializing vector store...")
    vector_store = VectorStore()
    print("   ✓ Vector store initialized")
    
    # Load sample policies
    print("\n2. Loading sample policies...")
    data_dir = Path(__file__).parent.parent / "data" / "sample_policies"
    
    policies = []
    for policy_file in data_dir.glob("*.json"):
        policy = load_policy_file(str(policy_file))
        policies.append(policy)
        print(f"   ✓ Loaded: {policy['policy_name']} ({policy['policy_id']})")
    
    # Add policies to vector store
    print("\n3. Adding policies to vector database...")
    for policy in policies:
        # Convert policy to text for embedding
        policy_text = f"""
        Policy: {policy['policy_name']}
        Policy ID: {policy['policy_id']}
        
        Coverage Rules:
        {json.dumps(policy['coverage_rules'], indent=2)}
        
        Deductible: ${policy['deductible']}
        Annual Maximum: ${policy['annual_maximum']}
        """
        
        vector_store.add_policy(
            policy_id=policy['policy_id'],
            policy_text=policy_text,
            metadata={
                "policy_name": policy['policy_name'],
                "deductible": policy['deductible'],
                "annual_maximum": policy['annual_maximum']
            }
        )
        print(f"   ✓ Added: {policy['policy_id']}")
    
    # Search for relevant policies
    print("\n4. Searching for relevant policies...")
    query = "MRI scan coverage"
    print(f"   Query: '{query}'")
    
    results = vector_store.search_similar(query, top_k=2)
    print(f"\n   Found {len(results)} relevant policies:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['id']} (Score: {result['score']:.4f})")
        if 'metadata' in result:
            print(f"      Policy: {result['metadata'].get('policy_name', 'N/A')}")
    
    # Use Policy Validator with RAG
    print("\n5. Using Policy Validator with RAG...")
    validator = PolicyValidator(vector_store=vector_store)
    
    treatment = "MRI scan of brain"
    claim_amount = 1500.0
    patient_metadata = {
        "insurance_plan": "Standard Health Insurance Plan",
        "deductible_remaining": 500
    }
    
    print(f"   Treatment: {treatment}")
    print(f"   Claim Amount: ${claim_amount:,.2f}")
    
    validation_result = validator.validate_treatment(
        treatment_description=treatment,
        patient_metadata=patient_metadata,
        claim_amount=claim_amount
    )
    
    print("\n6. Validation Results:")
    print(json.dumps(validation_result, indent=2))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"Covered: {'Yes' if validation_result.get('is_covered') else 'No'}")
    print(f"Coverage: {validation_result.get('coverage_percentage', 0)}%")
    print(f"Co-pay: ${validation_result.get('copay_amount', 0):.2f}")
    print(f"Policies Consulted: {validation_result.get('policies_consulted', 0)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
