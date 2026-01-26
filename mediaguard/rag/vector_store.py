"""Vector store interface for policy storage and retrieval."""

from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from mediaguard.rag.embeddings import EmbeddingGenerator

load_dotenv()


class VectorStore:
    """Interface for vector database operations (Pinecone or Milvus)."""
    
    def __init__(self, provider: str = "pinecone"):
        """Initialize the vector store.
        
        Args:
            provider: Vector database provider ("pinecone" or "milvus")
        """
        self.provider = provider
        self.embedding_generator = EmbeddingGenerator()
        self.index = None
        self._initialize_store()
    
    def _initialize_store(self):
        """Initialize the vector database connection."""
        if self.provider == "pinecone":
            self._initialize_pinecone()
        elif self.provider == "milvus":
            self._initialize_milvus()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _initialize_pinecone(self):
        """Initialize Pinecone vector database."""
        try:
            import pinecone
            
            api_key = os.getenv("PINECONE_API_KEY")
            environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
            index_name = os.getenv("PINECONE_INDEX_NAME", "mediguard-policies")
            
            if not api_key:
                raise ValueError("PINECONE_API_KEY not found in environment variables")
            
            # Initialize Pinecone
            pinecone.init(api_key=api_key, environment=environment)
            
            # Get or create index
            if index_name not in pinecone.list_indexes():
                # Create index if it doesn't exist
                dimension = self.embedding_generator.get_embedding_dimension()
                pinecone.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine"
                )
            
            self.index = pinecone.Index(index_name)
            self.index_name = index_name
            
        except ImportError:
            raise ImportError("pinecone not installed. Install with: pip install pinecone")
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
            raise ImportError("pymilvus not installed. Install with: pip install pymilvus")
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
            self.index.upsert(vectors=[(policy_id, embedding, metadata or {})])
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
            return [
                {
                    "id": match["id"],
                    "score": match["score"],
                    "metadata": match.get("metadata", {})
                }
                for match in results.get("matches", [])
            ]
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
        # For Pinecone, we'd need to store text separately or in metadata
        return None
