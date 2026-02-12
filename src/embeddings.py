"""
Vector embeddings manager for semantic code search using ChromaDB.
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import hashlib

from ast_parser import CodeEntity


class CodeEmbeddingManager:
    """
    Manages vector embeddings for code entities and files.
    Enables semantic search over codebase.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize embedding manager.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        # Using a lightweight model for local deployment
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create or get collections
        self.entity_collection = self.client.get_or_create_collection(
            name="code_entities",
            metadata={"description": "Code functions, classes, and methods"}
        )
        
        self.file_collection = self.client.get_or_create_collection(
            name="code_files",
            metadata={"description": "Complete code files"}
        )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        embedding = self.embedding_model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    def _create_entity_text(self, entity: CodeEntity, code_content: str) -> str:
        """
        Create searchable text representation of a code entity.
        
        Args:
            entity: CodeEntity object
            code_content: Source code content
            
        Returns:
            Text representation for embedding
        """
        # Extract entity code
        lines = code_content.split('\n')
        entity_code = '\n'.join(lines[entity.start_line - 1:entity.end_line])
        
        # Create rich text representation
        text_parts = [
            f"# {entity.type}: {entity.name}",
            f"# File: {entity.file_path}"
        ]
        
        if entity.parent_class:
            text_parts.append(f"# Class: {entity.parent_class}")
        
        if entity.docstring:
            text_parts.append(f"# Documentation: {entity.docstring}")
        
        text_parts.append(entity_code)
        
        return '\n'.join(text_parts)
    
    def add_entity(self, entity: CodeEntity, code_content: str):
        """
        Add code entity to vector database.
        
        Args:
            entity: CodeEntity to add
            code_content: Full source code content
        """
        entity_id = f"{entity.file_path}::{entity.name}"
        
        # Create searchable text
        entity_text = self._create_entity_text(entity, code_content)
        
        # Generate embedding
        embedding = self._generate_embedding(entity_text)
        
        # Store in ChromaDB
        self.entity_collection.add(
            ids=[entity_id],
            embeddings=[embedding],
            documents=[entity_text],
            metadatas=[{
                'name': entity.name,
                'type': entity.type,
                'file_path': entity.file_path,
                'start_line': entity.start_line,
                'end_line': entity.end_line,
                'parent_class': entity.parent_class or ''
            }]
        )
    
    def add_file(self, file_path: str, content: str, summary: Optional[str] = None):
        """
        Add complete file to vector database.
        
        Args:
            file_path: Path to the file
            content: File content
            summary: Optional file summary
        """
        file_id = hashlib.md5(file_path.encode()).hexdigest()
        
        # Create searchable text
        text_parts = [f"# File: {file_path}"]
        if summary:
            text_parts.append(f"# Summary: {summary}")
        text_parts.append(content)
        
        file_text = '\n'.join(text_parts)
        
        # Generate embedding
        embedding = self._generate_embedding(file_text)
        
        # Store in ChromaDB
        self.file_collection.add(
            ids=[file_id],
            embeddings=[embedding],
            documents=[file_text],
            metadatas=[{
                'file_path': file_path,
                'has_summary': summary is not None
            }]
        )
    
    def search_entities(self, query: str, n_results: int = 5,
                       entity_type: Optional[str] = None) -> List[Dict]:
        """
        Search for code entities semantically.
        
        Args:
            query: Natural language query
            n_results: Number of results to return
            entity_type: Optional filter by entity type ('function', 'class', 'method')
            
        Returns:
            List of matching entities with metadata
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Build filter
        where_filter = None
        if entity_type:
            where_filter = {"type": entity_type}
        
        # Search
        results = self.entity_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )
        
        # Format results
        formatted_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'name': results['metadatas'][0][i]['name'],
                    'type': results['metadatas'][0][i]['type'],
                    'file_path': results['metadatas'][0][i]['file_path'],
                    'start_line': results['metadatas'][0][i]['start_line'],
                    'end_line': results['metadatas'][0][i]['end_line'],
                    'distance': results['distances'][0][i] if 'distances' in results else None,
                    'code': results['documents'][0][i]
                })
        
        return formatted_results
    
    def search_files(self, query: str, n_results: int = 3) -> List[Dict]:
        """
        Search for files semantically.
        
        Args:
            query: Natural language query
            n_results: Number of results to return
            
        Returns:
            List of matching files with metadata
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Search
        results = self.file_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'file_path': results['metadatas'][0][i]['file_path'],
                    'distance': results['distances'][0][i] if 'distances' in results else None,
                    'content': results['documents'][0][i]
                })
        
        return formatted_results
    
    def update_entity(self, entity: CodeEntity, code_content: str):
        """Update an entity's embedding."""
        # Delete old entry
        entity_id = f"{entity.file_path}::{entity.name}"
        try:
            self.entity_collection.delete(ids=[entity_id])
        except:
            pass
        
        # Add new entry
        self.add_entity(entity, code_content)
    
    def delete_file_entities(self, file_path: str):
        """Delete all entities from a file."""
        # Query all entities from this file
        results = self.entity_collection.get(
            where={"file_path": file_path}
        )
        
        if results['ids']:
            self.entity_collection.delete(ids=results['ids'])
    
    def get_statistics(self) -> Dict:
        """Get embedding database statistics."""
        entity_count = self.entity_collection.count()
        file_count = self.file_collection.count()
        
        return {
            'total_entities': entity_count,
            'total_files': file_count,
            'embedding_model': 'all-MiniLM-L6-v2',
            'embedding_dimension': 384
        }
    
    def reset(self):
        """Clear all data from the database."""
        self.client.reset()
        self.__init__(self.persist_directory)
