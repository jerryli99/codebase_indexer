# quick_c_test.py
from pathlib import Path
import sys

# Add your project to path
sys.path.insert(0, '/home/jerry/codebase_indexer/src')

from ast_parser import ASTParser

# Initialize parser with debug mode
parser = ASTParser(debug=True)

# Test C file - adjust path to your actual C file
c_file = Path('/home/jerry/codebase_indexer/test/c_project/math_ops.c')

print("\n" + "="*60)
print("🔬 QUICK C PARSER TEST")
print("="*60)

# Check if file exists
print(f"\n📁 Testing file: {c_file}")
print(f"   File exists? {c_file.exists()}")
if c_file.exists():
    print(f"   File size: {c_file.stat().st_size} bytes")
    
    # Read first few lines
    with open(c_file, 'r') as f:
        lines = f.readlines()[:5]
        print("   First few lines:")
        for i, line in enumerate(lines, 1):
            print(f"     {i}: {line.rstrip()}")
    
    # Try to parse
    print("\n🔄 Attempting to parse...")
    tree = parser.parse_file(str(c_file))
    
    if tree:
        print(f"✅ SUCCESS! Root node: {tree.root_node.type}")
        
        # Extract entities
        print("\n🔍 Extracting entities...")
        entities = parser.extract_entities(str(c_file))
        
        if entities:
            print(f"✅ Found {len(entities)} entities:")
            for e in entities:
                print(f"   - {e.name} ({e.type}) lines {e.start_line}-{e.end_line}")
        else:
            print("❌ No entities extracted")
    else:
        print("❌ Parse failed")
else:
    print("❌ File not found!")

print("\n" + "="*60)
print("Available parsers:", list(parser.parsers.keys()))
print("="*60)