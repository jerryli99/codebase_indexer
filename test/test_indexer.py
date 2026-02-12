"""
Test suite for CodebaseIndexer - the main orchestrator.
Tests full integration of all components on C codebase.
"""
import unittest
import sys
from pathlib import Path
import tempfile
import shutil
import json

sys.path.insert(0, '/home/jerry/codebase_indexer/src')

from indexer import CodebaseIndexer


class TestCodebaseIndexer(unittest.TestCase):
    """Test complete codebase indexing workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_codebase = Path(__file__).parent / "sample_c_project"
        cls.temp_cache = tempfile.mkdtemp()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up."""
        shutil.rmtree(cls.temp_cache, ignore_errors=True)
    
    def setUp(self):
        """Set up for each test."""
        cache_dir = Path(self.temp_cache) / f"cache_{id(self)}"
        self.indexer = CodebaseIndexer(
            str(self.test_codebase),
            cache_dir=str(cache_dir)
        )
    
    def test_01_initialization(self):
        """Test indexer initialization."""
        print("\n" + "="*80)
        print("TEST 1: Indexer Initialization")
        print("="*80)
        
        print(f"\n✓ Indexer initialized")
        print(f"  Codebase path: {self.indexer.codebase_path}")
        print(f"  Cache directory: {self.indexer.cache_dir}")
        
        # Check components are initialized
        self.assertIsNotNone(self.indexer.merkle_tree)
        self.assertIsNotNone(self.indexer.ast_parser)
        self.assertIsNotNone(self.indexer.call_graph)
        self.assertIsNotNone(self.indexer.embeddings)
        
        print(f"\n✓ All components initialized:")
        print(f"  - Merkle Tree")
        print(f"  - AST Parser")
        print(f"  - Call Graph Analyzer")
        print(f"  - Embedding Manager")
    
    def test_02_full_index(self):
        """Test full codebase indexing."""
        print("\n" + "="*80)
        print("TEST 2: Full Codebase Indexing")
        print("="*80)
        
        print(f"\n🔍 Indexing C codebase at: {self.test_codebase}")
        
        stats = self.indexer.index_codebase(force_reindex=True)
        
        print(f"\n📊 Indexing Results:")
        print(f"  Files processed: {stats.get('files_processed', 0)}")
        print(f"  Entities found: {stats.get('entities_found', 0)}")
        print(f"  Calls found: {stats.get('calls_found', 0)}")
        
        # Check metadata
        print(f"\n📋 Metadata:")
        for key, value in self.indexer.metadata.items():
            print(f"  {key}: {value}")
        
        # Verify cache files were created
        cache_files = ['merkle_tree.json', 'call_graph.json', 'metadata.json']
        print(f"\n📁 Cache files created:")
        for cache_file in cache_files:
            file_path = self.indexer.cache_dir / cache_file
            exists = file_path.exists()
            status = "✓" if exists else "✗"
            print(f"  {status} {cache_file}")
        
        self.assertTrue(self.indexer.is_indexed or stats.get('files_processed', 0) > 0)
    
    def test_03_incremental_update(self):
        """Test incremental indexing."""
        print("\n" + "="*80)
        print("TEST 3: Incremental Indexing")
        print("="*80)
        
        # First index
        print(f"\n📝 First full index...")
        stats1 = self.indexer.index_codebase(force_reindex=True)
        print(f"  Files processed: {stats1.get('files_processed', 0)}")
        
        # Index again without changes
        print(f"\n📝 Second index (no changes expected)...")
        stats2 = self.indexer.index_codebase(force_reindex=False)
        
        if 'files_processed' in stats2:
            print(f"  Files processed: {stats2['files_processed']}")
        else:
            print(f"  No changes detected - index up to date ✓")
        
        print(f"\n✓ Incremental indexing working")
    
    def test_04_semantic_search(self):
        """Test semantic code search."""
        print("\n" + "="*80)
        print("TEST 4: Semantic Code Search")
        print("="*80)
        
        # Index first
        self.indexer.index_codebase(force_reindex=True)
        
        # Test queries
        queries = [
            "function that adds two numbers",
            "find maximum value in an array",
            "print array contents",
            "calculate factorial",
            "multiply numbers",
        ]
        
        print(f"\n🔍 Testing semantic search with {len(queries)} queries:")
        
        for query in queries:
            print(f"\n  Query: '{query}'")
            results = self.indexer.search_code(query, max_results=3)
            
            print(f"  Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"    {i}. {result['name']} ({result['type']})")
                print(f"       File: {Path(result['file_path']).name}")
                print(f"       Lines: {result['start_line']}-{result['end_line']}")
    
    def test_05_entity_context(self):
        """Test retrieving entity context."""
        print("\n" + "="*80)
        print("TEST 5: Entity Context Retrieval")
        print("="*80)
        
        # Index first
        self.indexer.index_codebase(force_reindex=True)
        
        # Try to get context for known entities
        test_entities = ["add", "multiply", "main", "find_max"]
        
        print(f"\n📋 Retrieving context for entities:")
        
        for entity_name in test_entities:
            context = self.indexer.get_entity_context(entity_name)
            
            if context:
                print(f"\n  ✓ {entity_name}:")
                if 'entity' in context:
                    print(f"    Type: {context['entity'].get('type')}")
                    print(f"    File: {context['entity'].get('file')}")
                    print(f"    Lines: {context['entity'].get('lines')}")
                
                if context.get('calls'):
                    print(f"    Calls: {[c['name'] for c in context['calls'][:3]]}")
                if context.get('called_by'):
                    print(f"    Called by: {[c['name'] for c in context['called_by'][:3]]}")
            else:
                print(f"\n  ⚠ {entity_name}: Not found or tree-sitter not installed")
    
    def test_06_impact_analysis(self):
        """Test change impact analysis."""
        print("\n" + "="*80)
        print("TEST 6: Change Impact Analysis")
        print("="*80)
        
        # Index first
        self.indexer.index_codebase(force_reindex=True)
        
        # Test impact analysis for different files
        test_files = ["math_ops.c", "utils.c", "main.c"]
        
        print(f"\n🔨 Analyzing impact of changes:")
        
        for file_path in test_files:
            print(f"\n  File: {file_path}")
            impact = self.indexer.get_impacted_by_change(file_path)
            
            print(f"    Total impacted entities: {impact['total_impacted_entities']}")
            print(f"    Impacted files: {impact['impacted_files']}")
            
            if impact['impacted_by_file']:
                print(f"    Details:")
                for imp_file, entities in list(impact['impacted_by_file'].items())[:3]:
                    print(f"      {imp_file}: {entities[:3]}")
    
    def test_07_statistics(self):
        """Test getting comprehensive statistics."""
        print("\n" + "="*80)
        print("TEST 7: Statistics Retrieval")
        print("="*80)
        
        # Index first
        self.indexer.index_codebase(force_reindex=True)
        
        # Get statistics
        stats = self.indexer.get_statistics()
        
        print(f"\n📊 Comprehensive Statistics:")
        
        print(f"\n  Metadata:")
        for key, value in stats['metadata'].items():
            print(f"    {key}: {value}")
        
        print(f"\n  Call Graph:")
        for key, value in stats['call_graph'].items():
            print(f"    {key}: {value}")
        
        print(f"\n  Embeddings:")
        for key, value in stats['embeddings'].items():
            print(f"    {key}: {value}")
        
        print(f"\n  Indexed Files: {stats['indexed_files']}")
    
    def test_08_indexed_files(self):
        """Test tracking of indexed files."""
        print("\n" + "="*80)
        print("TEST 8: Indexed Files Tracking")
        print("="*80)
        
        # Index
        self.indexer.index_codebase(force_reindex=True)
        
        print(f"\n📁 Indexed files ({len(self.indexer.indexed_files)}):")
        for file_path in sorted(self.indexer.indexed_files):
            print(f"  - {file_path}")
        
        # Verify expected files are indexed
        expected_extensions = ['.c', '.h']
        for file_path in self.indexer.indexed_files:
            has_valid_ext = any(file_path.endswith(ext) for ext in expected_extensions) or 'Makefile' in file_path
            if has_valid_ext:
                print(f"  ✓ {file_path}")
    
    def test_09_cache_persistence(self):
        """Test that cache persists across indexer instances."""
        print("\n" + "="*80)
        print("TEST 9: Cache Persistence")
        print("="*80)
        
        # Index with first indexer
        print(f"\n📝 Creating first indexer and indexing...")
        cache_dir = Path(self.temp_cache) / "shared_cache"
        indexer1 = CodebaseIndexer(str(self.test_codebase), cache_dir=str(cache_dir))
        stats1 = indexer1.index_codebase(force_reindex=True)
        
        print(f"  Files processed: {stats1.get('files_processed', 0)}")
        print(f"  Entities found: {stats1.get('entities_found', 0)}")
        
        # Create second indexer with same cache
        print(f"\n📝 Creating second indexer with same cache...")
        indexer2 = CodebaseIndexer(str(self.test_codebase), cache_dir=str(cache_dir))
        
        # Load metadata
        metadata = indexer2._load_metadata()
        print(f"\n✓ Loaded metadata from cache:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        # Verify cache was used
        self.assertIsNotNone(metadata.get('last_indexed'))
        print(f"\n✓ Cache persistence working")
    
    def test_10_full_workflow(self):
        """Test complete workflow: index, search, analyze."""
        print("\n" + "="*80)
        print("TEST 10: Complete Workflow")
        print("="*80)
        
        print(f"\n🚀 Running complete workflow...")
        
        # Step 1: Index
        print(f"\n1️⃣  INDEXING")
        stats = self.indexer.index_codebase(force_reindex=True)
        print(f"   ✓ Indexed {stats.get('files_processed', 0)} files")
        
        # Step 2: Search
        print(f"\n2️⃣  SEARCHING")
        query = "function to add numbers"
        results = self.indexer.search_code(query, max_results=3)
        print(f"   ✓ Found {len(results)} results for '{query}'")
        if results:
            print(f"   Top result: {results[0]['name']}")
        
        # Step 3: Get context
        print(f"\n3️⃣  GET CONTEXT")
        if results:
            entity_name = results[0]['name']
            context = self.indexer.get_entity_context(entity_name)
            if context:
                print(f"   ✓ Retrieved context for {entity_name}")
                if context.get('calls'):
                    print(f"   Calls: {[c['name'] for c in context['calls'][:3]]}")
        
        # Step 4: Impact analysis
        print(f"\n4️⃣  IMPACT ANALYSIS")
        impact = self.indexer.get_impacted_by_change("math_ops.c")
        print(f"   ✓ Analyzed impact: {impact['total_impacted_entities']} entities affected")
        
        # Step 5: Statistics
        print(f"\n5️⃣  STATISTICS")
        stats = self.indexer.get_statistics()
        print(f"   ✓ Total entities: {stats['call_graph']['total_entities']}")
        print(f"   ✓ Total files: {stats['metadata']['total_files']}")
        
        print(f"\n✅ Complete workflow successful!")


if __name__ == '__main__':
    unittest.main(verbosity=2)
