"""
Setup script to load sample policies into the vector database.

Run this script to populate a persistent vector database (Pinecone) with the sample policies.
The in-memory store used for local demos is populated automatically by the app.
"""
from mediaguard.rag.vector_store import VectorStore
from mediaguard.rag.policy_loader import DEFAULT_POLICY_DIR, load_policy_dir


def main():
    """Load sample policies into vector database."""
    print("Setting up MediGuard policies...")
    print("=" * 60)

    if not DEFAULT_POLICY_DIR.exists():
        print(f"Error: Policies directory not found: {DEFAULT_POLICY_DIR}")
        return

    vector_store = VectorStore()
    loaded = load_policy_dir(vector_store, DEFAULT_POLICY_DIR)

    print("=" * 60)
    print(f"Total policies loaded: {loaded} (provider: {vector_store.provider})")
    print("\nPolicies are now available for RAG-based policy validation.")


if __name__ == "__main__":
    main()
