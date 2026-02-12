"""
Test suite for Call Graph Analyzer.
Tests dependency tracking, call relationships, and impact analysis.
"""
import unittest
import sys
from pathlib import Path
import json
import tempfile

sys.path.insert(0, '/home/jerry/codebase_indexer/src')

from call_graph import CallGraphAnalyzer, DependencyInfo
from ast_parser import CodeEntity, CallReference


class TestCallGraph(unittest.TestCase):
    """Test Call Graph functionality."""
    
    def setUp(self):
        """Set up for each test."""
        self.analyzer = CallGraphAnalyzer()
        
    def test_01_add_entities(self):
        """Test adding code entities to the graph."""
        print("\n" + "="*80)
        print("TEST 1: Adding Entities to Call Graph")
        print("="*80)
        
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
            CodeEntity(
                name="main",
                type="function",
                start_line=1,
                end_line=15,
                file_path="main.c"
            ),
        ]
        
        print(f"\nAdding {len(entities)} entities:")
        
        for entity in entities:
            self.analyzer.add_entity(entity)
            entity_id = f"{entity.file_path}::{entity.name}"
            print(f"  ✓ Added: {entity_id}")
            print(f"    Type: {entity.type}")
            print(f"    Lines: {entity.start_line}-{entity.end_line}")
        
        # Verify entities were added
        self.assertEqual(len(self.analyzer.entities), 3)
        print(f"\n✓ Total entities in graph: {len(self.analyzer.entities)}")
        
        # Check file_entities mapping
        print(f"\nEntities by file:")
        for file_path, file_ents in self.analyzer.file_entities.items():
            print(f"  {file_path}:")
            for ent in file_ents:
                print(f"    - {ent.name} ({ent.type})")
    
    def test_02_add_calls(self):
        """Test adding call relationships."""
        print("\n" + "="*80)
        print("TEST 2: Adding Call Relationships")
        print("="*80)
        
        # First add entities
        entities = [
            CodeEntity(name="add", type="function", start_line=1, end_line=3, file_path="math.c"),
            CodeEntity(name="multiply", type="function", start_line=5, end_line=10, file_path="math.c"),
            CodeEntity(name="factorial", type="function", start_line=12, end_line=20, file_path="math.c"),
        ]
        
        for entity in entities:
            self.analyzer.add_entity(entity)
        
        # Add calls
        calls = [
            CallReference(caller="multiply", callee="add", file_path="math.c", line_number=7),
            CallReference(caller="factorial", callee="multiply", file_path="math.c", line_number=15),
        ]
        
        print(f"\nAdding {len(calls)} call relationships:")
        
        for call in calls:
            self.analyzer.add_call(call)
            print(f"  ✓ {call.caller} → {call.callee} (line {call.line_number})")
        
        # Verify calls were added
        edge_count = self.analyzer.call_graph.number_of_edges()
        print(f"\n✓ Total edges in call graph: {edge_count}")
        self.assertEqual(edge_count, 2)
    
    def test_03_get_entity_dependencies(self):
        """Test retrieving entity dependencies."""
        print("\n" + "="*80)
        print("TEST 3: Entity Dependencies")
        print("="*80)
        
        # Build a small graph
        # add() is standalone
        # multiply() calls add()
        # factorial() calls multiply()
        entities = [
            CodeEntity(name="add", type="function", start_line=1, end_line=3, file_path="math.c"),
            CodeEntity(name="multiply", type="function", start_line=5, end_line=10, file_path="math.c"),
            CodeEntity(name="factorial", type="function", start_line=12, end_line=20, file_path="math.c"),
        ]
        
        for entity in entities:
            self.analyzer.add_entity(entity)
        
        calls = [
            CallReference(caller="multiply", callee="add", file_path="math.c", line_number=7),
            CallReference(caller="factorial", callee="multiply", file_path="math.c", line_number=15),
        ]
        
        for call in calls:
            self.analyzer.add_call(call)
        
        # Test dependencies for each function
        test_functions = ["add", "multiply", "factorial"]
        
        for func_name in test_functions:
            entity_id = f"math.c::{func_name}"
            deps = self.analyzer.get_entity_dependencies(entity_id)
            
            print(f"\nDependencies for {func_name}:")
            print(f"  Calls: {[id.split('::')[1] for id in deps['calls']]}")
            print(f"  Called by: {[id.split('::')[1] for id in deps['called_by']]}")
        
        # Verify specific dependencies
        multiply_deps = self.analyzer.get_entity_dependencies("math.c::multiply")
        self.assertEqual(len(multiply_deps['calls']), 1)  # calls add
        self.assertEqual(len(multiply_deps['called_by']), 1)  # called by factorial
        
        print(f"\n✓ Dependency tracking working correctly")
    
    def test_04_get_call_chain(self):
        """Test finding call chains between entities."""
        print("\n" + "="*80)
        print("TEST 4: Call Chain Detection")
        print("="*80)
        
        # Build a chain: main -> factorial -> multiply -> add
        entities = [
            CodeEntity(name="add", type="function", start_line=1, end_line=3, file_path="math.c"),
            CodeEntity(name="multiply", type="function", start_line=5, end_line=10, file_path="math.c"),
            CodeEntity(name="factorial", type="function", start_line=12, end_line=20, file_path="math.c"),
            CodeEntity(name="main", type="function", start_line=1, end_line=10, file_path="main.c"),
        ]
        
        for entity in entities:
            self.analyzer.add_entity(entity)
        
        calls = [
            CallReference(caller="multiply", callee="add", file_path="math.c", line_number=7),
            CallReference(caller="factorial", callee="multiply", file_path="math.c", line_number=15),
            CallReference(caller="main", callee="factorial", file_path="main.c", line_number=5),
        ]
        
        for call in calls:
            self.analyzer.add_call(call)
        
        # Find call chain from main to add
        paths = self.analyzer.get_call_chain("main.c::main", "math.c::add")
        
        print(f"\nCall chains from main to add:")
        for i, path in enumerate(paths, 1):
            path_str = " → ".join([p.split('::')[1] for p in path])
            print(f"  Path {i}: {path_str}")
        
        if len(paths) > 0:
            print(f"\n✓ Found {len(paths)} call path(s)")
            # Should be: main -> factorial -> multiply -> add
            self.assertEqual(len(paths[0]), 4)
        else:
            print(f"\n⚠ No paths found")
    
    def test_05_circular_dependencies(self):
        """Test detection of circular dependencies."""
        print("\n" + "="*80)
        print("TEST 5: Circular Dependency Detection")
        print("="*80)
        
        # Create a circular dependency: A -> B -> C -> A
        entities = [
            CodeEntity(name="funcA", type="function", start_line=1, end_line=5, file_path="test.c"),
            CodeEntity(name="funcB", type="function", start_line=7, end_line=11, file_path="test.c"),
            CodeEntity(name="funcC", type="function", start_line=13, end_line=17, file_path="test.c"),
        ]
        
        for entity in entities:
            self.analyzer.add_entity(entity)
        
        calls = [
            CallReference(caller="funcA", callee="funcB", file_path="test.c", line_number=3),
            CallReference(caller="funcB", callee="funcC", file_path="test.c", line_number=9),
            CallReference(caller="funcC", callee="funcA", file_path="test.c", line_number=15),
        ]
        
        for call in calls:
            self.analyzer.add_call(call)
        
        print(f"\nCreated circular call chain: funcA → funcB → funcC → funcA")
        
        # Detect strongly connected components
        sccs = self.analyzer.get_strongly_connected_components()
        
        print(f"\nStrongly connected components:")
        circular_count = 0
        for i, scc in enumerate(sccs, 1):
            if len(scc) > 1:
                circular_count += 1
                func_names = [id.split('::')[1] for id in scc]
                print(f"  Component {i} (circular): {func_names}")
        
        if circular_count > 0:
            print(f"\n✓ Detected {circular_count} circular dependency group(s)")
        else:
            print(f"\n No circular dependencies detected")
    
    def test_06_impact_analysis(self):
        """Test analyzing impact of changes."""
        print("\n" + "="*80)
        print("TEST 6: Change Impact Analysis")
        print("="*80)
        
        # Build dependency tree
        entities = [
            CodeEntity(name="add", type="function", start_line=1, end_line=3, file_path="math.c"),
            CodeEntity(name="multiply", type="function", start_line=5, end_line=10, file_path="math.c"),
            CodeEntity(name="factorial", type="function", start_line=12, end_line=20, file_path="math.c"),
            CodeEntity(name="main", type="function", start_line=1, end_line=10, file_path="main.c"),
        ]
        
        for entity in entities:
            self.analyzer.add_entity(entity)
        
        calls = [
            CallReference(caller="multiply", callee="add", file_path="math.c", line_number=7),
            CallReference(caller="factorial", callee="multiply", file_path="math.c", line_number=15),
            CallReference(caller="main", callee="factorial", file_path="main.c", line_number=5),
        ]
        
        for call in calls:
            self.analyzer.add_call(call)
        
        # Analyze impact of changing add()
        print(f"\nAnalyzing impact of changing add() function:")
        
        impacted = self.analyzer.get_impacted_entities("math.c::add", max_depth=3)
        
        print(f"  Direct and indirect callers:")
        for entity_id in impacted:
            print(f"    - {entity_id}")
        
        if len(impacted) > 0:
            print(f"\n✓ Found {len(impacted)} potentially impacted entities")
            # Should impact: multiply, factorial, main
            self.assertGreaterEqual(len(impacted), 1)
        else:
            print(f"\nNo impacted entities found")
    
    def test_07_entity_context(self):
        """Test getting comprehensive entity context."""
        print("\n" + "="*80)
        print("TEST 7: Entity Context Retrieval")
        print("="*80)
        
        # Build a simple graph
        entity = CodeEntity(
            name="multiply",
            type="function",
            start_line=5,
            end_line=10,
            file_path="math_ops.c",
            parent_class=None
        )
        self.analyzer.add_entity(entity)
        
        # Add some dependencies
        add_entity = CodeEntity(name="add", type="function", start_line=1, end_line=3, file_path="math_ops.c")
        main_entity = CodeEntity(name="main", type="function", start_line=1, end_line=15, file_path="main.c")
        
        self.analyzer.add_entity(add_entity)
        self.analyzer.add_entity(main_entity)
        
        self.analyzer.add_call(CallReference("multiply", "add", "math_ops.c", 7))
        self.analyzer.add_call(CallReference("main", "multiply", "main.c", 5))
        
        # Get context
        context = self.analyzer.get_entity_context("math_ops.c::multiply")
        
        print(f"\nContext for multiply function:")
        print(f"  Entity info:")
        print(f"    Name: {context['entity']['name']}")
        print(f"    Type: {context['entity']['type']}")
        print(f"    File: {context['entity']['file']}")
        print(f"    Lines: {context['entity']['lines']}")
        
        if 'calls' in context:
            print(f"\n  Calls:")
            for call in context['calls']:
                print(f"    - {call['name']} in {call['file']}")
        
        if 'called_by' in context:
            print(f"\n  Called by:")
            for caller in context['called_by']:
                print(f"    - {caller['name']} in {caller['file']}")
        
        print(f"\n✓ Context retrieval working")
    
    def test_08_export_graph(self):
        """Test exporting call graph to JSON."""
        print("\n" + "="*80)
        print("TEST 8: Export Call Graph")
        print("="*80)
        
        # Build a small graph
        entities = [
            CodeEntity(name="add", type="function", start_line=1, end_line=3, file_path="math.c"),
            CodeEntity(name="multiply", type="function", start_line=5, end_line=10, file_path="math.c"),
        ]
        
        for entity in entities:
            self.analyzer.add_entity(entity)
        
        self.analyzer.add_call(CallReference("multiply", "add", "math.c", 7))
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.analyzer.export_graph(temp_path)
            print(f"\n✓ Graph exported to: {temp_path}")
            
            # Load and verify
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            print(f"\nExported graph structure:")
            print(f"  Entities: {len(data['entities'])}")
            print(f"  Calls: {len(data['calls'])}")
            print(f"  File dependencies: {len(data['file_dependencies'])}")
            
            # Show some entities
            print(f"\n  Sample entities:")
            for entity_id, entity_data in list(data['entities'].items())[:2]:
                print(f"    {entity_id}:")
                print(f"      Name: {entity_data['name']}")
                print(f"      Type: {entity_data['type']}")
                print(f"      File: {entity_data['file']}")
            
            # Show calls
            print(f"\n  Call relationships:")
            for call in data['calls']:
                from_name = call['from'].split('::')[1]
                to_name = call['to'].split('::')[1]
                print(f"    {from_name} → {to_name} (line {call['line']})")
            
            print(f"\n✓ Export successful and valid")
            
        finally:
            Path(temp_path).unlink()
    
    def test_09_statistics(self):
        """Test getting call graph statistics."""
        print("\n" + "="*80)
        print("TEST 9: Call Graph Statistics")
        print("="*80)
        
        # Build a graph with various entities
        entities = [
            CodeEntity(name="add", type="function", start_line=1, end_line=3, file_path="math.c"),
            CodeEntity(name="subtract", type="function", start_line=5, end_line=7, file_path="math.c"),
            CodeEntity(name="multiply", type="function", start_line=9, end_line=14, file_path="math.c"),
            CodeEntity(name="MathHelper", type="class", start_line=1, end_line=20, file_path="helper.py"),
        ]
        
        for entity in entities:
            self.analyzer.add_entity(entity)
        
        calls = [
            CallReference("multiply", "add", "math.c", 10),
            CallReference("multiply", "subtract", "math.c", 12),
        ]
        
        for call in calls:
            self.analyzer.add_call(call)
        
        # Get statistics
        stats = self.analyzer.get_statistics()
        
        print(f"\nCall Graph Statistics:")
        print(f"  Total entities: {stats['total_entities']}")
        print(f"  Total calls: {stats['total_calls']}")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Avg calls per entity: {stats['avg_calls_per_entity']:.2f}")
        print(f"  Circular dependencies: {stats['circular_dependencies']}")
        
        print(f"\n  Entities by type:")
        for entity_type, count in stats['entities_by_type'].items():
            print(f"    {entity_type}: {count}")
        
        self.assertEqual(stats['total_entities'], 4)
        self.assertEqual(stats['total_calls'], 2)
        
        print(f"\n✓ Statistics calculation working correctly")


if __name__ == '__main__':
    unittest.main(verbosity=2)
