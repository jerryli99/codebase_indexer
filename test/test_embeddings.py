"""
Test suite for Code Embedding Manager.
Tests vector embeddings, semantic search, and ChromaDB integration.
"""
import unittest
import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, '/home/jerry/codebase_indexer/src')

from embeddings import CodeEmbeddingManager
from ast_parser import CodeEntity


class TestEmbeddings(unittest.TestCase):
    """Test Embedding Manager functionality."""
    
    def setUp(self):
        """Set up for each test with temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = CodeEmbeddingManager(persist_directory=self.temp_dir)
        
    def tearDown(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_01_initialization(self):
        """Test embedding manager initialization."""
        print("\n" + "="*80)
        print("TEST 1: Embedding Manager Initialization")
        print("="*80)
        
        print(f"\n✓ Manager initialized")
        print(f"  Persist directory: {self.temp_dir}")
        print(f"  Embedding model: {self.manager.embedding_model}")
        print(f"  Entity collection: {self.manager.entity_collection.name}")
        print(f"  File collection: {self.manager.file_collection.name}")
        
        # Check collections exist
        self.assertIsNotNone(self.manager.entity_collection)
        self.assertIsNotNone(self.manager.file_collection)
        
        print(f"\n✓ ChromaDB collections created successfully")
    
    def test_02_generate_embedding(self):
        """Test embedding generation."""
        print("\n" + "="*80)
        print("TEST 2: Generate Embeddings")
        print("="*80)
        
        test_texts = [
            "int add(int a, int b) { return a + b; }",
            "void print_array(int arr[], int size) { for(int i=0; i<size; i++) printf(\"%d \", arr[i]); }",
            "Calculate factorial of a number"
        ]
        
        print(f"\nGenerating embeddings for {len(test_texts)} texts:")
        
        for i, text in enumerate(test_texts, 1):
            embedding = self.manager._generate_embedding(text)
            
            print(f"\n  Text {i}: {text[:50]}...")
            print(f"    Embedding dimension: {len(embedding)}")
            print(f"    First 5 values: {[f'{v:.4f}' for v in embedding[:5]]}")
            print(f"    Last 5 values: {[f'{v:.4f}' for v in embedding[-5:]]}")
            
            # Verify embedding properties
            self.assertEqual(len(embedding), 384)  # all-MiniLM-L6-v2 dimension
            self.assertTrue(all(isinstance(v, float) for v in embedding))
        
        print(f"\n✓ Embedding generation working correctly")
    
    def test_03_add_entity(self):
        """Test adding code entities to vector database."""
        print("\n" + "="*80)
        print("TEST 3: Add Code Entities")
        print("="*80)
        
        # Create sample C entities
        entities = [
            CodeEntity(
                name="add",
                type="function",
                start_line=1,
                end_line=3,
                file_path="math_ops.c"
            ),
            CodeEntity(
                name="multiply",
                type="function",
                start_line=5,
                end_line=10,
                file_path="math_ops.c"
            ),
        ]
        
        code_content = """int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    int result = 0;
    for (int i = 0; i < b; i++) {
        result = add(result, a);
    }
    return result;
}"""
        
        print(f"\nAdding {len(entities)} entities to vector database:")
        
        for entity in entities:
            self.manager.add_entity(entity, code_content)
            print(f"  ✓ Added: {entity.name} ({entity.type})")
        
        # Verify entities were added
        count = self.manager.entity_collection.count()
        print(f"\n✓ Total entities in database: {count}")
        self.assertEqual(count, 2)
    
    def test_04_add_file(self):
        """Test adding complete files to vector database."""
        print("\n" + "="*80)
        print("TEST 4: Add Files")
        print("="*80)
        
        files = [
            {
                'path': 'main.c',
                'content': '#include <stdio.h>\nint main() { return 0; }',
                'summary': 'Main entry point of the program'
            },
            {
                'path': 'utils.c',
                'content': 'void helper() { printf("Help"); }',
                'summary': None
            },
        ]
        
        print(f"\nAdding {len(files)} files:")
        
        for file_data in files:
            self.manager.add_file(
                file_data['path'],
                file_data['content'],
                file_data['summary']
            )
            summary_str = f" (with summary)" if file_data['summary'] else ""
            print(f"  ✓ Added: {file_data['path']}{summary_str}")
        
        count = self.manager.file_collection.count()
        print(f"\n✓ Total files in database: {count}")
        self.assertEqual(count, 2)
    
    def test_05_search_entities(self):
        """Test semantic search for code entities."""
        print("\n" + "="*80)
        print("TEST 5: Semantic Search for Entities")
        print("="*80)
        
        # Add sample entities
        entities_data = [
            ("add", "function", "int add(int a, int b) { return a + b; }"),
            ("subtract", "function", "int subtract(int a, int b) { return a - b; }"),
            ("multiply", "function", "int multiply(int a, int b) { return a * b; }"),
            ("find_max", "function", "int find_max(int arr[], int size) { int max = arr[0]; for(int i=1; i<size; i++) if(arr[i]>max) max=arr[i]; return max; }"),
            ("print_array", "function", "void print_array(int arr[], int size) { for(int i=0; i<size; i++) printf(\"%d \", arr[i]); }"),
        ]
        
        for name, ent_type, code in entities_data:
            entity = CodeEntity(
                name=name,
                type=ent_type,
                start_line=1,
                end_line=5,
                file_path="test.c"
            )
            self.manager.add_entity(entity, code)
        
        print(f"\n✓ Added {len(entities_data)} entities")
        
        # Test searches
        queries = [
            "function that adds two numbers",
            "find maximum value in array",
            "display array elements",
            "arithmetic operations",
        ]
        
        print(f"\n🔍 Testing semantic search:")
        
        for query in queries:
            print(f"\n  Query: '{query}'")
            results = self.manager.search_entities(query, n_results=3)
            
            print(f"  Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"    {i}. {result['name']} ({result['type']})")
                print(f"       File: {result['file_path']}")
                print(f"       Distance: {result['distance']:.4f}")
                print(f"       Code preview: {result['code'][:60]}...")
            
            self.assertGreater(len(results), 0)
        
        print(f"\n✓ Semantic search working correctly")
    
    def test_06_search_by_type(self):
        """Test filtering search by entity type."""
        print("\n" + "="*80)
        print("TEST 6: Search with Type Filtering")
        print("="*80)
        
        # Add entities of different types
        entities_data = [
            ("add", "function", "int add(int a, int b) { return a + b; }"),
            ("Calculator", "class", "class Calculator { public: int add(int a, int b); };"),
            ("helper", "function", "void helper() { printf(\"help\"); }"),
        ]
        
        for name, ent_type, code in entities_data:
            entity = CodeEntity(
                name=name,
                type=ent_type,
                start_line=1,
                end_line=5,
                file_path="test.c"
            )
            self.manager.add_entity(entity, code)
        
        # Search for functions only
        print(f"\nSearching for functions only:")
        results = self.manager.search_entities("addition", n_results=5, entity_type="function")
        
        print(f"  Found {len(results)} results:")
        for result in results:
            print(f"    - {result['name']} ({result['type']})")
        
        # Verify all results are functions
        for result in results:
            self.assertEqual(result['type'], 'function')
        
        print(f"\n✓ Type filtering working correctly")
    
    def test_07_update_entity(self):
        """Test updating entity embeddings."""
        print("\n" + "="*80)
        print("TEST 7: Update Entity")
        print("="*80)
        
        # Add initial entity
        entity = CodeEntity(
            name="calculate",
            type="function",
            start_line=1,
            end_line=3,
            file_path="test.c"
        )
        
        old_code = "int calculate(int x) { return x * 2; }"
        self.manager.add_entity(entity, old_code)
        
        print(f"\nInitial entity added:")
        print(f"  Code: {old_code}")
        
        # Search for it
        results_before = self.manager.search_entities("multiply by two", n_results=1)
        print(f"\n  Search result: {results_before[0]['name']}")
        
        # Update the entity
        new_code = "int calculate(int x) { return x * x; }"
        self.manager.update_entity(entity, new_code)
        
        print(f"\nEntity updated:")
        print(f"  New code: {new_code}")
        
        # Search again
        results_after = self.manager.search_entities("square a number", n_results=1)
        print(f"\n  New search result: {results_after[0]['name']}")
        
        # Verify count stayed the same (update, not add)
        count = self.manager.entity_collection.count()
        self.assertEqual(count, 1)
        
        print(f"\n✓ Entity update working correctly")
    
    def test_08_delete_file_entities(self):
        """Test deleting all entities from a file."""
        print("\n" + "="*80)
        print("TEST 8: Delete File Entities")
        print("="*80)
        
        # Add entities from multiple files
        files_entities = {
            "file1.c": ["func1", "func2"],
            "file2.c": ["func3", "func4"],
        }
        
        for file_path, func_names in files_entities.items():
            for func_name in func_names:
                entity = CodeEntity(
                    name=func_name,
                    type="function",
                    start_line=1,
                    end_line=3,
                    file_path=file_path
                )
                self.manager.add_entity(entity, f"void {func_name}() {{}}")
        
        initial_count = self.manager.entity_collection.count()
        print(f"\nInitial state:")
        print(f"  Total entities: {initial_count}")
        print(f"  Entities in file1.c: {len(files_entities['file1.c'])}")
        print(f"  Entities in file2.c: {len(files_entities['file2.c'])}")
        
        # Delete file1.c entities
        print(f"\n Deleting all entities from file1.c...")
        self.manager.delete_file_entities("file1.c")
        
        final_count = self.manager.entity_collection.count()
        print(f"\nAfter deletion:")
        print(f"  Total entities: {final_count}")
        
        expected_count = len(files_entities['file2.c'])
        self.assertEqual(final_count, expected_count)
        
        print(f"\n✓ File deletion working correctly")
    
    def test_09_get_statistics(self):
        """Test getting embedding database statistics."""
        print("\n" + "="*80)
        print("TEST 9: Embedding Statistics")
        print("="*80)
        
        # Add some data
        for i in range(5):
            entity = CodeEntity(
                name=f"func{i}",
                type="function",
                start_line=1,
                end_line=3,
                file_path=f"file{i}.c"
            )
            self.manager.add_entity(entity, f"void func{i}() {{}}")
            self.manager.add_file(f"file{i}.c", f"void func{i}() {{}}")
        
        # Get statistics
        stats = self.manager.get_statistics()
        
        print(f"\n Embedding Database Statistics:")
        print(f"  Total entities: {stats['total_entities']}")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Embedding model: {stats['embedding_model']}")
        print(f"  Embedding dimension: {stats['embedding_dimension']}")
        
        self.assertEqual(stats['total_entities'], 5)
        self.assertEqual(stats['total_files'], 5)
        self.assertEqual(stats['embedding_dimension'], 384)
        
        print(f"\n✓ Statistics retrieval working correctly")
    
    def test_10_similarity_ranking(self):
        """Test that results are ranked by semantic similarity."""
        print("\n" + "="*80)
        print("TEST 10: Similarity Ranking")
        print("="*80)
        
        # Add entities with varying relevance to query
        entities_data = [
            ("add_numbers", "function", "int add_numbers(int a, int b) { return a + b; }"),
            ("multiply", "function", "int multiply(int a, int b) { return a * b; }"),
            ("print_string", "function", "void print_string(char* s) { printf(\"%s\", s); }"),
            ("sum_array", "function", "int sum_array(int arr[], int size) { int sum=0; for(int i=0; i<size; i++) sum+=arr[i]; return sum; }"),
        ]
        
        for name, ent_type, code in entities_data:
            entity = CodeEntity(
                name=name,
                type=ent_type,
                start_line=1,
                end_line=5,
                file_path="test.c"
            )
            self.manager.add_entity(entity, code)
        
        # Query for addition-related functions
        query = "add two integers together"
        results = self.manager.search_entities(query, n_results=4)
        
        print(f"\n Query: '{query}'")
        print(f"\n  Results (ranked by similarity):")
        
        for i, result in enumerate(results, 1):
            print(f"    {i}. {result['name']}")
            print(f"       Distance: {result['distance']:.4f} (lower is better)")
        
        # Verify results are sorted by distance (ascending)
        distances = [r['distance'] for r in results]
        self.assertEqual(distances, sorted(distances))
        
        # The most relevant should be add_numbers or sum_array
        top_result = results[0]['name']
        print(f"\n✓ Most relevant result: {top_result}")
        print(f"✓ Results properly ranked by semantic similarity")


if __name__ == '__main__':
    unittest.main(verbosity=2)
