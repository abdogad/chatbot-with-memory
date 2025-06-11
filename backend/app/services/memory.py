import os
import uuid
from pinecone import Pinecone
from typing import List
from datetime import datetime
    

class MemoryService:
    def __init__(self):
        # Initialize Pinecone
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        
        # Initialize Pinecone
        pinecone = Pinecone(api_key=pinecone_api_key)
        
        index_name = "crayon-ai"

        if not pinecone.has_index(index_name):
            pinecone.create_index_for_model(
                name=index_name,
                cloud="aws",
                region="us-east-1",
                embed={
                    "model":"llama-text-embed-v2",
                    "field_map":{"text": "chunk_text"}
                }
            )
        
        # Connect to the index
        self.index = pinecone.Index(index_name)
    
    
    async def store_memory(self, user_id: str, content: str, role: str) -> str:
        """Store a new memory in the vector store"""

        memory_id = str(uuid.uuid4())
        print(f"Storing memory with ID: {memory_id} for user: {user_id}")
        self.index.upsert_records(
            records=[
                {
                    "id": memory_id,
                    "chunk_text": content,
                    "timestamp": datetime.now().timestamp(),
                    "role": role
                }
            ],
            namespace=user_id
        )
        print(f"Memory stored successfully with ID: {memory_id}")
        return memory_id
    
    async def search_memories(self, user_id: str, query: str, limit: int = 3) -> List[dict]:
        """Search for relevant memories using semantic search"""
        try:
            
            # Query Pinecone
            results = self.index.search(
                namespace=user_id,
                query={
                    "top_k": limit,
                    "inputs": {
                        "text" : query
                    }
                }
            )
            
            print(results.result.hits)
            return results.result.hits
        except Exception as e:
            print(f"Error searching memories: {str(e)}")
            return []
    
    def _namespace_exists(self, user_id: str) -> bool:
        """Check if a namespace exists for a user"""
        namespaces = self.index.describe_index_stats()
        print(f"Available namespaces: {namespaces}")
        return namespaces.namespaces.get(user_id) is not None
            
    async def clear_memories(self, user_id: str) -> bool:
        """Clear all memories for a user"""
        try:
            print(f"Clearing memories for user: {user_id}")
            
            # First, list all vectors in the namespace
            try:
                # Get all vector IDs in the namespace
                stats = self.index.describe_index_stats()
                if user_id not in stats.namespaces:
                    print(f"No memories found for user: {user_id}")
                    return True
                    
                # Delete the entire namespace
                self.index.delete(delete_all=True, namespace=user_id)
                print(f"Successfully cleared memories for user: {user_id}")
                return True
                
            except Exception as e:
                print(f"Error during memory cleanup: {str(e)}")
                # Fallback to deleting all vectors in the namespace
                try:
                    # Get all vector IDs in the namespace
                    vector_ids = list(self.index.list(prefix="", namespace=user_id))
                    if vector_ids:
                        self.index.delete(ids=vector_ids, namespace=user_id)
                    return True
                except Exception as inner_e:
                    print(f"Fallback cleanup failed: {str(inner_e)}")
                    return False
                    
        except Exception as e:
            print(f"Error clearing memories: {str(e)}")
            return False
    
    async def get_history(self, user_id: str, limit: int = 15) -> List[dict]:
        ids = self.index.list(namespace=user_id)
        print(f"Fetched IDs: {ids}")
        ids = [id for id in ids if id is not None]
        if ids == []:
            return []
        ids = ids[0]
    
        print(f"IDs: {ids}")
        data = self.index.fetch(ids, namespace=user_id)
        
        # Convert to list of dictionaries and sort by metadata text
        history = []
        for id, vector_data in data.vectors.items():
            history.append({
                'id': id,
                'timestamp': vector_data.metadata.get("timestamp",0),
                'text': vector_data.metadata.get("chunk_text",""),
                'role': vector_data.metadata.get("role", "user")
            })
        
        # Sort by text in metadata
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        history = history[:limit]
        history.reverse()
        # remove timestamp and id and rename text to parts also make it a list
        for entry in history:
            entry['parts'] = [entry.pop('text')]
            entry.pop('timestamp')
            entry.pop('id')
        print(f"History: {history}")
        return history[:limit]
    