"""Vector store interface for policy storage and retrieval."""

from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from mediaguard.rag.embeddings import EmbeddingGenerator

load_dotenv()


class VectorStore:
    """Interface for vector database operations (Pinecone, Milvus or in-memory)."""
    
    def __init__(self, provider: str = None):
        """Initialize the vector store.
        
        Args:
            provider: "pinecone", "milvus" or "memory" (defaults to VECTOR_DB_PROVIDER, else "pinecone").
                Pinecone/Milvus fall back to the in-memory store when unavailable.
        """
        self.provider = (provider or os.getenv("VECTOR_DB_PROVIDER", "pinecone")).lower()
        self.embedding_generator = EmbeddingGenerator()
        self.index = None
        self._initialize_store()
    
    def _initialize_store(self):
        """Initialize the vector database connection."""
        if self.provider == "pinecone":
            self._initialize_pinecone()
        elif self.provider == "milvus":
            self._initialize_milvus()
        elif self.provider == "memory":
            self._initialize_memory_store()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _initialize_pinecone(self):
        """Initialize Pinecone (serverless, pinecone>=5 client)."""
        try:
            from pinecone import Pinecone, ServerlessSpec
        except ImportError:
            print("Warning: pinecone not installed (pip install pinecone). Using in-memory storage.")
            self._initialize_memory_store()
            return
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                raise ValueError("PINECONE_API_KEY not found in environment variables")
            index_name = os.getenv("PINECONE_INDEX_NAME", "mediguard-policies")
            pc = Pinecone(api_key=api_key)
            if not pc.has_index(index_name):
                pc.create_index(
                    name=index_name,
                    dimension=self.embedding_generator.get_embedding_dimension(),
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=os.getenv("PINECONE_CLOUD", "aws"),
                        region=os.getenv("PINECONE_REGION", os.getenv("PINECONE_ENVIRONMENT", "us-east-1")),
                    ),
                )
            self.index = pc.Index(index_name)
            self.index_name = index_name
        except Exception as e:
            print(f"Warning: Could not initialize Pinecone: {e}")
            print("Falling back to in-memory storage for demonstration.")
            self._initialize_memory_store()
    
    def _initialize_milvus(self):
        """Initialize Milvus vector database."""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
            
            host = os.getenv("MILVUS_HOST", "localhost")
            port = os.getenv("MILVUS_PORT", "19530")
            
            # Connect to Milvus
            connections.connect("default", host=host, port=port)
            
            # Collection setup would go here
            # For now, fall back to memory store
            self._initialize_memory_store()
            
        except ImportError:
            print("Warning: pymilvus not installed (pip install pymilvus). Using in-memory storage.")
            self._initialize_memory_store()
        except Exception as e:
            print(f"Warning: Could not initialize Milvus: {e}")
            print("Falling back to in-memory storage for demonstration.")
            self._initialize_memory_store()
    
    def _initialize_memory_store(self):
        """Initialize in-memory vector store for demonstration."""
        self.memory_store = []
        self.provider = "memory"
    
    def add_policy(self, policy_id: str, policy_text: str, metadata: Dict[str, Any] = None):
        """Add a policy document to the vector store.
        
        Args:
            policy_id: Unique identifier for the policy
            policy_text: Text content of the policy
            metadata: Additional metadata to store with the policy
        """
        embedding = self.embedding_generator.generate_embedding(policy_text)
        
        if self.provider == "pinecone" and self.index:
            # Add to Pinecone
            # Pinecone stores metadata only, so keep the policy text there for retrieval.
            self.index.upsert(vectors=[(policy_id, embedding, {**(metadata or {}), "text": policy_text})])
        elif self.provider == "memory":
            # Add to memory store
            self.memory_store.append({
                "id": policy_id,
                "embedding": embedding,
                "text": policy_text,
                "metadata": metadata or {}
            })
    
    def search_similar(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar policies.
        
        Args:
            query_text: Query text to search for
            top_k: Number of results to return
            
        Returns:
            List of similar policies with scores
        """
        query_embedding = self.embedding_generator.generate_embedding(query_text)
        
        if self.provider == "pinecone" and self.index:
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            matches = getattr(results, "matches", None)
            if matches is None:
                matches = results.get("matches", [])
            out = []
            for match in matches:
                get = (lambda k: getattr(match, k, None)) if not isinstance(match, dict) else match.get
                meta = dict(get("metadata") or {})
                out.append({
                    "id": get("id"),
                    "score": get("score"),
                    "text": meta.pop("text", ""),
                    "metadata": meta,
                })
            return out
        elif self.provider == "memory":
            # Search memory store using cosine similarity
            import numpy as np
            
            query_vec = np.array(query_embedding)
            results = []
            
            for item in self.memory_store:
                item_vec = np.array(item["embedding"])
                # Cosine similarity
                similarity = np.dot(query_vec, item_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(item_vec)
                )
                results.append({
                    "id": item["id"],
                    "score": float(similarity),
                    "text": item["text"],
                    "metadata": item["metadata"]
                })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        
        return []
    
    def get_policy_text(self, policy_id: str) -> Optional[str]:
        """Retrieve full text of a policy by ID.
        
        Args:
            policy_id: ID of the policy to retrieve
            
        Returns:
            Policy text if found, None otherwise
        """
        if self.provider == "memory":
            for item in self.memory_store:
                if item["id"] == policy_id:
                    return item["text"]
        if self.provider == "pinecone" and self.index:
            fetched = self.index.fetch(ids=[policy_id])
            vectors = getattr(fetched, "vectors", None) or {}
            if policy_id in vectors:
                return (vectors[policy_id].metadata or {}).get("text")
        return None

    def count(self) -> int:
        """Number of stored policies (best effort for remote stores)."""
        if self.provider == "memory":
            return len(self.memory_store)
        if self.provider == "pinecone" and self.index:
            return int(self.index.describe_index_stats().get("total_vector_count", 0))
        return 0
