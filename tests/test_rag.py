"""Tests for RAG modules."""

import pytest
from mediaguard.rag.embeddings import EmbeddingGenerator
from mediaguard.rag.vector_store import VectorStore


def test_embedding_generator():
    """Test embedding generation."""
    generator = EmbeddingGenerator()
    
    text = "Test text for embedding"
    embedding = generator.generate_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, (int, float)) for x in embedding)


def test_vector_store_memory():
    """Test in-memory vector store."""
    vector_store = VectorStore(provider="memory")
    
    # Add a policy
    vector_store.add_policy(
        policy_id="TEST-001",
        policy_text="MRI scan coverage: 80%",
        metadata={"type": "test"}
    )
    
    # Search
    results = vector_store.search_similar("MRI scan", top_k=1)
    
    assert len(results) > 0
    assert results[0]["id"] == "TEST-001"


if __name__ == "__main__":
    pytest.main([__file__])
