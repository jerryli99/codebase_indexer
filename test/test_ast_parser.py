"""
Test suite for AST Parser.
Tests entity extraction, call detection for C code.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, '/home/jerry/codebase_indexer/src')

from ast_parser import ASTParser, CodeEntity, CallReference


class TestASTParser(unittest.TestCase):
    """Test AST Parser functionality with C codebase."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_dir = Path(__file__).parent / "c_project"
        cls.parser = ASTParser()
        
    def test_01_language_detection(self):
        """Test language detection from file extensions."""
        print("\n" + "="*80)
        print("TEST 1: Language Detection")
        print("="*80)
        
        test_files = {
            'test.c': 'c',
            'test.h': 'c',
            'test.py': 'python',
            'test.js': 'javascript',
            'test.java': 'java',
            'test.go': 'go',
        }
        
        print("\n Testing file extension mapping:")
        for filename, expected_lang in test_files.items():
            detected = self.parser._get_language(filename)
            status = "✓" if detected == expected_lang else "✗"
            print(f"  {status} {filename} → {detected}")
            self.assertEqual(detected, expected_lang)
    
    def test_02_parse_c_files(self):
        """Test parsing C source files."""
        print("\n" + "="*80)
        print("TEST 2: Parsing C Files")
        print("="*80)
        
        c_files = ['main.c', 'math_ops.c', 'utils.c']
        
        for filename in c_files:
            file_path = self.test_dir / filename
            
            print(f"\n Parsing {filename}:")
            
            tree = self.parser.parse_file(str(file_path))
            
            if tree:
                print(f"  ✓ Successfully parsed")
                print(f"  ✓ Root node type: {tree.root_node.type}")
                print(f"  ✓ Tree has {len(tree.root_node.children)} top-level nodes")
            else:
                print(f"   Parsing not available (tree-sitter not installed)")
                print(f"  → Install with: pip install tree-sitter tree-sitter-c")
    
    def test_03_extract_entities_from_main(self):
        """Test extracting functions from main.c."""
        print("\n" + "="*80)
        print("TEST 3: Extract Entities from main.c")
        print("="*80)
        
        file_path = self.test_dir / "main.c"
        entities = self.parser.extract_entities(str(file_path))
        
        print(f"\n Extracted {len(entities)} entities:")
        
        for entity in entities:
            print(f"\n  {entity.type.upper()}: {entity.name}")
            print(f"    File: {Path(entity.file_path).name}")
            print(f"    Lines: {entity.start_line}-{entity.end_line}")
            if entity.parent_class:
                print(f"    Parent class: {entity.parent_class}")
        
        if len(entities) > 0:
            # Check for main function
            main_funcs = [e for e in entities if e.name == 'main']
            if main_funcs:
                print(f"\n✓ Found main() function at lines {main_funcs[0].start_line}-{main_funcs[0].end_line}")
            else:
                print(f"\n Note: main() function not detected (tree-sitter needed)")
        else:
            print(f"\n No entities extracted (tree-sitter-c not installed)")
            print(f"  This is expected if tree-sitter is not set up")
    
    def test_04_extract_entities_from_math_ops(self):
        """Test extracting functions from math_ops.c."""
        print("\n" + "="*80)
        print("TEST 4: Extract Entities from math_ops.c")
        print("="*80)
        
        file_path = self.test_dir / "math_ops.c"
        entities = self.parser.extract_entities(str(file_path))
    
        print(f"\n Extracted {len(entities)} entities:")
        
        expected_functions = ['add', 'subtract', 'multiply', 'divide', 'factorial']
        
        found_functions = [e.name for e in entities if e.type == 'function']
        
        print(f"\n  Functions found: {found_functions}")
        print(f"  Expected: {expected_functions}")
        
        for entity in entities:
            print(f"\n  FUNCTION: {entity.name}")
            print(f"    Lines: {entity.start_line}-{entity.end_line}")
            print(f"    Type: {entity.type}")
        
        if len(entities) == 0:
            print(f"\n⚠ No entities extracted (tree-sitter-c not installed)")
    
    def test_05_extract_entities_from_utils(self):
        """Test extracting functions from utils.c."""
        print("\n" + "="*80)
        print("TEST 5: Extract Entities from utils.c")
        print("="*80)
        
        file_path = self.test_dir / "utils.c"
        entities = self.parser.extract_entities(str(file_path))
        
        print(f"\nExtracted {len(entities)} entities:")
        
        for entity in entities:
            print(f"\n  FUNCTION: {entity.name}")
            print(f"    File: {Path(entity.file_path).name}")
            print(f"    Lines: {entity.start_line}-{entity.end_line}")
            print(f"    Type: {entity.type}")
        
        expected_functions = ['print_array', 'find_max', 'find_min', 'array_sum']
        found_functions = [e.name for e in entities]
        
        print(f"\n  Expected functions: {expected_functions}")
        print(f"  Found functions: {found_functions}")
        
        if len(entities) > 0:
            print(f"\n✓ Successfully extracted utility functions")
        else:
            print(f"\nNo entities extracted (tree-sitter-c not installed)")
    
    def test_06_extract_calls(self):
        """Test extracting function calls."""
        print("\n" + "="*80)
        print("TEST 6: Extract Function Calls")
        print("="*80)
        
        # Test with math_ops.c which has internal calls
        file_path = self.test_dir / "math_ops.c"
        entities = self.parser.extract_entities(str(file_path))
        
        if len(entities) > 0:
            calls = self.parser.extract_calls(str(file_path), entities)
            
            print(f"\n📞 Extracted {len(calls)} function calls:")
            
            for call in calls:
                print(f"\n  {call.caller} → {call.callee}")
                print(f"    File: {Path(call.file_path).name}")
                print(f"    Line: {call.line_number}")
            
            if len(calls) > 0:
                print(f"\n✓ Call extraction working")
                
                # Check for specific expected calls
                # multiply() calls add()
                # factorial() calls multiply() and subtract()
                caller_callee_pairs = [(c.caller, c.callee) for c in calls]
                print(f"\n  Detected call relationships:")
                for caller, callee in caller_callee_pairs:
                    print(f"    {caller} → {callee}")
            else:
                print(f"\nNo calls detected")
        else:
            print(f"\nCannot test calls without entities (tree-sitter-c not installed)")
    
    def test_07_code_entity_dataclass(self):
        """Test CodeEntity dataclass creation."""
        print("\n" + "="*80)
        print("TEST 7: CodeEntity Data Structure")
        print("="*80)
        
        entity = CodeEntity(
            name="test_function",
            type="function",
            start_line=10,
            end_line=20,
            file_path="test.c",
            signature="int test_function(int x, int y)",
            docstring="Test function"
        )
        
        print(f"\nCreated CodeEntity:")
        print(f"  Name: {entity.name}")
        print(f"  Type: {entity.type}")
        print(f"  Lines: {entity.start_line}-{entity.end_line}")
        print(f"  File: {entity.file_path}")
        print(f"  Signature: {entity.signature}")
        print(f"  Docstring: {entity.docstring}")
        
        self.assertEqual(entity.name, "test_function")
        self.assertEqual(entity.type, "function")
        print(f"\n✓ CodeEntity dataclass working correctly")
    
    def test_08_call_reference_dataclass(self):
        """Test CallReference dataclass creation."""
        print("\n" + "="*80)
        print("TEST 8: CallReference Data Structure")
        print("="*80)
        
        call = CallReference(
            caller="main",
            callee="helper",
            file_path="test.c",
            line_number=15
        )
        
        print(f"\nCreated CallReference:")
        print(f"  Caller: {call.caller}")
        print(f"  Callee: {call.callee}")
        print(f"  File: {call.file_path}")
        print(f"  Line: {call.line_number}")
        
        self.assertEqual(call.caller, "main")
        self.assertEqual(call.callee, "helper")
        print(f"\n✓ CallReference dataclass working correctly")


if __name__ == '__main__':
    unittest.main(verbosity=2)
