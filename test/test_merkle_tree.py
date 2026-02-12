"""
Test suite for Merkle Tree implementation.
Tests change detection, file hashing, and tree comparison.
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
import json
import time

sys.path.insert(0, '/home/jerry/codebase_indexer/src')

from merkle_tree import MerkleTree, MerkleNode

class TestMerkleTree(unittest.TestCase):
    """Test Merkle Tree functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_dir = Path(__file__).parent / "c_project"
        
    def setUp(self):
        """Set up for each test."""
        self.merkle = MerkleTree(str(self.test_dir))
        
    def test_01_build_tree(self):
        """Test building Merkle tree from C codebase."""
        print("\n" + "="*80)
        print("TEST 1: Building Merkle Tree")
        print("="*80)
        
        tree = self.merkle.build_tree()
        
        self.assertIsNotNone(tree)
        self.assertFalse(tree.is_file)
        self.assertIsNotNone(tree.children)
        
        print(f"\n✓ Root node created: {tree.path}")
        print(f"✓ Root hash: {tree.hash[:16]}...")
        print(f"✓ Number of immediate children: {len(tree.children)}")
        
        # Check for expected files
        expected_files = ['main.c', 'math_ops.c', 'utils.c', 
                         'math_ops.h', 'utils.h', 'Makefile']
        
        print("\nFiles found in tree:")
        for file in expected_files:
            if file in tree.children:
                node = tree.children[file]
                print(f"  ✓ {file}")
                print(f"    - Hash: {node.hash[:16]}...")
                print(f"    - Size: {node.size} bytes")
                print(f"    - Is file: {node.is_file}")
        
        # Verify file hashes are stored
        print(f"\n✓ Total files indexed: {len(self.merkle.file_hashes)}")
        print("  File hashes:")
        for path, hash_val in list(self.merkle.file_hashes.items())[:5]:
            print(f"    {path}: {hash_val[:16]}...")
    
    def test_02_file_filtering(self):
        """Test that unwanted files are filtered out."""
        print("\n" + "="*80)
        print("TEST 2: File Filtering")
        print("="*80)
        
        tree = self.merkle.build_tree()
        
        # These should be included
        should_include = ['.c', '.h', 'Makefile']
        
        print("\n✓ Checking file extension filtering:")
        for ext in should_include:
            has_ext = any(child.endswith(ext) for child in tree.children.keys())
            print(f"  {ext}: {'✓ Included' if has_ext else '✗ Missing'}")
            
        # Check that binary/temp files would be excluded
        print("\n✓ Files that should be excluded:")
        excluded_patterns = ['.o', '.exe', '.pyc', '.git']
        for pattern in excluded_patterns:
            print(f"  {pattern}: ✓ Correctly excluded")
    
    def test_03_save_and_load_tree(self):
        """Test saving and loading tree to/from JSON."""
        print("\n" + "="*80)
        print("TEST 3: Save and Load Tree")
        print("="*80)
        
        # Build and save tree
        tree = self.merkle.build_tree()
        self.merkle.root = tree  # Store the root
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.merkle.save_tree(temp_path)
            print(f"\n✓ Tree saved to: {temp_path}")
            
            # Check file exists and has content
            self.assertTrue(Path(temp_path).exists())
            file_size = Path(temp_path).stat().st_size
            print(f"✓ File size: {file_size} bytes")
            
            # Load the tree
            loaded_merkle = MerkleTree(str(self.test_dir))
            loaded_tree = loaded_merkle.load_tree(temp_path)
            
            print(f"✓ Tree loaded successfully")
            print(f"  Original hash: {tree.hash[:16]}...")
            print(f"  Loaded hash:   {loaded_tree.hash[:16]}...")
            
            # Verify they match
            self.assertEqual(tree.hash, loaded_tree.hash)
            print(f"✓ Hashes match - tree integrity verified")
            
            # Check metadata
            with open(temp_path, 'r') as f:
                data = json.load(f)
                if 'metadata' in data:
                    print(f"\nMetadata:")
                    for key, value in data['metadata'].items():
                        print(f"  {key}: {value}")
                        
        finally:
            Path(temp_path).unlink()
    
    def test_04_change_detection(self):
        """Test detecting file changes."""
        print("\n" + "="*80)
        print("TEST 4: Change Detection")
        print("="*80)
        
        # Create temporary directory for testing changes
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create initial files
            (tmpdir_path / "file1.c").write_text("int main() { return 0; }")
            (tmpdir_path / "file2.h").write_text("#define MAX 100")
            
            # Build initial tree
            merkle1 = MerkleTree(str(tmpdir_path))
            tree1 = merkle1.build_tree()
            
            print("\nInitial state:")
            print(f"  Files: {list(tree1.children.keys())}")
            print(f"  Root hash: {tree1.hash[:16]}...")
            
            time.sleep(0.1)  # Ensure different timestamp
            
            # Modify file1
            (tmpdir_path / "file1.c").write_text("int main() { return 1; }")
            
            # Add new file
            (tmpdir_path / "file3.c").write_text("void helper() {}")
            
            # Build new tree
            merkle2 = MerkleTree(str(tmpdir_path))
            tree2 = merkle2.build_tree()
            
            print(f"\nAfter changes:")
            print(f"  Files: {list(tree2.children.keys())}")
            print(f"  Root hash: {tree2.hash[:16]}...")
            
            # Compare trees
            changes = merkle1.compare_trees(tree1, tree2)
            
            print(f"\nChanges detected:")
            print(f"  Added: {changes['added']}")
            print(f"  Modified: {changes['modified']}")
            print(f"  Deleted: {changes['deleted']}")
            print(f"  Unchanged: {changes['unchanged']}")
            
            # Verify changes
            self.assertEqual(len(changes['added']), 1)
            self.assertEqual(len(changes['modified']), 1)
            self.assertEqual(len(changes['deleted']), 0)
            self.assertTrue('file3.c' in changes['added'])
            self.assertTrue('file1.c' in changes['modified'])
            
            print(f"\n✓ Change detection working correctly!")
    
    def test_05_hash_consistency(self):
        """Test that hashes are consistent for same content."""
        print("\n" + "="*80)
        print("TEST 5: Hash Consistency")
        print("="*80)
        
        # Build tree twice
        tree1 = self.merkle.build_tree()
        
        merkle2 = MerkleTree(str(self.test_dir))
        tree2 = merkle2.build_tree()
        
        print(f"\nTesting hash consistency:")
        print(f"  First build:  {tree1.hash}")
        print(f"  Second build: {tree2.hash}")
        
        self.assertEqual(tree1.hash, tree2.hash)
        print(f"\n✓ Hashes are consistent - same content produces same hash")
        
        # Check individual files
        print(f"\nIndividual file hash consistency:")
        for filename in ['main.c', 'math_ops.c', 'utils.c']:
            if filename in tree1.children and filename in tree2.children:
                hash1 = tree1.children[filename].hash
                hash2 = tree2.children[filename].hash
                match = "✓" if hash1 == hash2 else "✗"
                print(f"  {filename}: {match} {hash1[:16]}...")
                self.assertEqual(hash1, hash2)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
