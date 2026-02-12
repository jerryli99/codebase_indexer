"""
Main CodebaseIndexer orchestrator that coordinates all components.
"""
from pathlib import Path
from typing import Dict, List, Set, Optional
import json
from datetime import datetime

from merkle_tree import MerkleTree
from ast_parser import ASTParser, CodeEntity
from call_graph import CallGraphAnalyzer
from embeddings import CodeEmbeddingManager


class CodebaseIndexer:
    """
    Main orchestrator for codebase indexing and analysis.
    Coordinates Merkle trees, AST parsing, call graphs, and embeddings.
    """
    
    def __init__(self, codebase_path: str, cache_dir: str = "./.codebase_cache"):
        """
        Initialize codebase indexer.
        
        Args:
            codebase_path: Path to codebase root
            cache_dir: Directory for caching index data
        """
        self.codebase_path = Path(codebase_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize components
        self.merkle_tree = MerkleTree(str(self.codebase_path))
        self.ast_parser = ASTParser()
        self.call_graph = CallGraphAnalyzer()
        self.embeddings = CodeEmbeddingManager(
            persist_directory=str(self.cache_dir / "chroma_db")
        )
        
        # State
        self.is_indexed = False
        self.indexed_files: Set[str] = set()
        self.metadata = {
            'last_indexed': None,
            'total_files': 0,
            'total_entities': 0
        }
    
    def index_codebase(self, force_reindex: bool = False) -> Dict:
        """
        Index the entire codebase.
        
        Args:
            force_reindex: Force complete reindexing
            
        Returns:
            Indexing statistics
        """
        print("Starting codebase indexing...")
        
        # Build Merkle tree
        print("Building Merkle tree...")
        tree = self.merkle_tree.build_tree()
        self.merkle_tree.root = tree
        
        # Save tree state
        tree_path = self.cache_dir / "merkle_tree.json"
        self.merkle_tree.save_tree(str(tree_path))
        
        # Check for incremental update
        changes = None
        if not force_reindex and tree_path.exists():
            print("Checking for changes...")
            old_tree = self.merkle_tree.load_tree(str(tree_path))
            changes = self.merkle_tree.compare_trees(old_tree, tree)
            
            if not any(changes.values()):
                print("No changes detected, index up to date")
                return self._load_metadata()
        
        # Index files
        if changes and not force_reindex:
            print(f"Processing incremental changes...")
            stats = self._index_changes(changes)
        else:
            print("Performing full index...")
            stats = self._index_all_files()
        
        # Update metadata
        self.metadata.update({
            'last_indexed': datetime.now().isoformat(),
            'total_files': len(self.indexed_files),
            'total_entities': len(self.call_graph.entities)
        })
        self._save_metadata()
        
        # Export call graph
        self.call_graph.export_graph(str(self.cache_dir / "call_graph.json"))
        
        print("Indexing complete!")
        return stats
    
    def _index_all_files(self) -> Dict:
        """Index all source files in codebase."""
        stats = {
            'files_processed': 0,
            'entities_found': 0,
            'calls_found': 0
        }
        
        # Find all source files
        source_files = []
        for ext in ['.py', '.js', '.ts', '.java', '.c', '.h', '.go']:
            source_files.extend(self.codebase_path.rglob(f"*{ext}"))
        
        # Process each file
        for file_path in source_files:
            if self._should_skip_file(file_path):
                continue
            
            file_stats = self._index_file(str(file_path.relative_to(self.codebase_path)))
            stats['files_processed'] += 1
            stats['entities_found'] += file_stats['entities']
            stats['calls_found'] += file_stats['calls']
        
        return stats
    
    def _index_changes(self, changes: Dict[str, Set[str]]) -> Dict:
        """Index only changed files."""
        stats = {
            'files_added': len(changes['added']),
            'files_modified': len(changes['modified']),
            'files_deleted': len(changes['deleted']),
            'entities_updated': 0
        }
        
        # Delete entities from deleted files
        for file_path in changes['deleted']:
            self.embeddings.delete_file_entities(file_path)
        
        # Index added and modified files
        for file_path in changes['added'] | changes['modified']:
            file_stats = self._index_file(file_path)
            stats['entities_updated'] += file_stats['entities']
        
        return stats
    
    def _index_file(self, relative_path: str) -> Dict:
        """
        Index a single file.
        
        Args:
            relative_path: Path relative to codebase root
            
        Returns:
            Statistics for this file
        """
        full_path = self.codebase_path / relative_path
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return {'entities': 0, 'calls': 0}
        
        # Extract entities
        entities = self.ast_parser.extract_entities(str(full_path))
        
        # Add entities to call graph and embeddings
        for entity in entities:
            self.call_graph.add_entity(entity)
            self.embeddings.add_entity(entity, content)
        
        # Extract calls
        calls = self.ast_parser.extract_calls(str(full_path), entities)
        
        # Add calls to graph
        for call in calls:
            self.call_graph.add_call(call)
        
        # Add file to embeddings
        self.embeddings.add_file(relative_path, content)
        
        self.indexed_files.add(relative_path)
        
        return {
            'entities': len(entities),
            'calls': len(calls)
        }
    
    def _should_skip_file(self, path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = {'__pycache__', 'node_modules', '.git', 'venv', 'env'}
        return any(pattern in path.parts for pattern in skip_patterns)
    
    def search_code(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search codebase semantically.
        
        Args:
            query: Natural language query
            max_results: Maximum results to return
            
        Returns:
            List of relevant code entities
        """
        return self.embeddings.search_entities(query, n_results=max_results)
    
    def get_entity_context(self, entity_name: str, file_path: Optional[str] = None) -> Dict:
        """
        Get comprehensive context for an entity.
        
        Args:
            entity_name: Name of the entity
            file_path: Optional file path to disambiguate
            
        Returns:
            Entity context with dependencies
        """
        # Find matching entity
        entity_id = None
        for eid, entity in self.call_graph.entities.items():
            if entity.name == entity_name:
                if file_path is None or entity.file_path == file_path:
                    entity_id = eid
                    break
        
        if not entity_id:
            return {}
        
        return self.call_graph.get_entity_context(entity_id)
    
    def get_impacted_by_change(self, file_path: str) -> Dict:
        """
        Analyze impact of changes to a file.
        
        Args:
            file_path: Changed file path
            
        Returns:
            Impact analysis
        """
        impacted_entities = set()
        
        # Get all entities in the file
        if file_path in self.call_graph.file_entities:
            for entity in self.call_graph.file_entities[file_path]:
                entity_id = f"{file_path}::{entity.name}"
                # Find all entities impacted by this change
                impacted = self.call_graph.get_impacted_entities(entity_id)
                impacted_entities.update(impacted)
        
        # Organize by file
        impacted_by_file = {}
        for entity_id in impacted_entities:
            if entity_id in self.call_graph.entities:
                entity = self.call_graph.entities[entity_id]
                if entity.file_path not in impacted_by_file:
                    impacted_by_file[entity.file_path] = []
                impacted_by_file[entity.file_path].append(entity.name)
        
        return {
            'changed_file': file_path,
            'total_impacted_entities': len(impacted_entities),
            'impacted_files': len(impacted_by_file),
            'impacted_by_file': impacted_by_file
        }
    
    def get_statistics(self) -> Dict:
        """Get comprehensive indexing statistics."""
        return {
            'metadata': self.metadata,
            'call_graph': self.call_graph.get_statistics(),
            'embeddings': self.embeddings.get_statistics(),
            'indexed_files': len(self.indexed_files)
        }
    
    def _save_metadata(self):
        """Save metadata to cache."""
        with open(self.cache_dir / "metadata.json", 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _load_metadata(self) -> Dict:
        """Load metadata from cache."""
        metadata_path = self.cache_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
        return self.metadata
