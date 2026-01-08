"""
Verification script to test MediGuard installation.

Run this script to verify that all components are properly installed.
"""

import sys
from pathlib import Path


def check_imports():
    """Check if all required modules can be imported."""
    print("Checking imports...")
    
    try:
        import openai
        print("  ✓ openai")
    except ImportError:
        print("  ✗ openai - Install with: pip install openai")
        return False
    
    try:
        import langchain
        print("  ✓ langchain")
    except ImportError:
        print("  ✗ langchain - Install with: pip install langchain")
        return False
    
    try:
        import langgraph
        print("  ✓ langgraph")
    except ImportError:
        print("  ✗ langgraph - Install with: pip install langgraph")
        return False
    
    try:
        from sentence_transformers import SentenceTransformer
        print("  ✓ sentence-transformers")
    except ImportError:
        print("  ✗ sentence-transformers - Install with: pip install sentence-transformers")
        return False
    
    try:
        import pinecone
        print("  ✓ pinecone-client (optional)")
    except ImportError:
        print("  ⚠ pinecone-client not installed (optional, will use in-memory storage)")
    
    return True


def check_mediaguard_modules():
    """Check if MediGuard modules can be imported."""
    print("\nChecking MediGuard modules...")
    
    try:
        from mediaguard.agents.triage_agent import TriageAgent
        print("  ✓ TriageAgent")
    except Exception as e:
        print(f"  ✗ TriageAgent - {e}")
        return False
    
    try:
        from mediaguard.agents.policy_validator import PolicyValidator
        print("  ✓ PolicyValidator")
    except Exception as e:
        print(f"  ✗ PolicyValidator - {e}")
        return False
    
    try:
        from mediaguard.agents.compliance_auditor import ComplianceAuditor
        print("  ✓ ComplianceAuditor")
    except Exception as e:
        print(f"  ✗ ComplianceAuditor - {e}")
        return False
    
    try:
        from mediaguard.rag.vector_store import VectorStore
        print("  ✓ VectorStore")
    except Exception as e:
        print(f"  ✗ VectorStore - {e}")
        return False
    
    try:
        from mediaguard.guardrails.phi_detector import PHIDetector
        print("  ✓ PHIDetector")
    except Exception as e:
        print(f"  ✗ PHIDetector - {e}")
        return False
    
    try:
        from mediaguard.orchestrator import MediGuardOrchestrator
        print("  ✓ MediGuardOrchestrator")
    except Exception as e:
        print(f"  ✗ MediGuardOrchestrator - {e}")
        return False
    
    return True


def check_environment():
    """Check environment configuration."""
    print("\nChecking environment...")
    
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("  ✓ OPENAI_API_KEY is set")
    else:
        print("  ⚠ OPENAI_API_KEY not set (required for LLM agents)")
        print("    Set it in .env file or environment variable")
    
    pinecone_key = os.getenv("PINECONE_API_KEY")
    if pinecone_key:
        print("  ✓ PINECONE_API_KEY is set")
    else:
        print("  ⚠ PINECONE_API_KEY not set (optional, will use in-memory storage)")
    
    return True


def check_data_files():
    """Check if sample data files exist."""
    print("\nChecking sample data files...")
    
    base_path = Path(__file__).parent
    
    policies_dir = base_path / "data" / "sample_policies"
    if policies_dir.exists():
        policy_files = list(policies_dir.glob("*.json"))
        print(f"  ✓ Found {len(policy_files)} policy file(s)")
    else:
        print("  ⚠ Sample policies directory not found")
    
    claims_dir = base_path / "data" / "sample_claims"
    if claims_dir.exists():
        claim_files = list(claims_dir.glob("*.txt"))
        print(f"  ✓ Found {len(claim_files)} claim file(s)")
    else:
        print("  ⚠ Sample claims directory not found")
    
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("MediGuard Installation Verification")
    print("=" * 60)
    
    all_checks = [
        check_imports(),
        check_mediaguard_modules(),
        check_environment(),
        check_data_files()
    ]
    
    print("\n" + "=" * 60)
    if all(all_checks):
        print("✓ All checks passed! MediGuard is ready to use.")
        print("\nNext steps:")
        print("  1. Set OPENAI_API_KEY in .env file")
        print("  2. Run: python examples/basic_usage.py")
        print("  3. Or run: python -m mediaguard.cli process --help")
    else:
        print("⚠ Some checks failed. Please review the errors above.")
        print("\nTo install missing dependencies:")
        print("  pip install -r requirements.txt")
    print("=" * 60)
    
    return 0 if all(all_checks) else 1


if __name__ == "__main__":
    sys.exit(main())
