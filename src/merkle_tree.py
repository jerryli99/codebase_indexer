"""
Merkle Tree implementation for efficient codebase change detection.

We take a snapshot of the repo state, compare old/new tree, detect added/modified/deleted files
"""
import hashlib
import json
from typing import Dict, List, Set, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import fnmatch
from datetime import datetime


@dataclass
class MerkleNode:
    """Represents a node in the Merkle tree."""
    path: str
    hash: str
    is_file: bool
    children: Optional[Dict[str, 'MerkleNode']] = None
    size: Optional[int] = None
    modified_time: Optional[float] = None
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'path': self.path,
            'hash': self.hash,
            'is_file': self.is_file,
            'children': {k: v.to_dict() for k, v in self.children.items()} if self.children else None,
            'size': self.size,
            'modified_time': self.modified_time
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MerkleNode':
        """Create MerkleNode from dictionary."""
        children = None
        if data.get('children'):
            children = {k: cls.from_dict(v) for k, v in data['children'].items()}
        return cls(
            path=data['path'],
            hash=data['hash'],
            is_file=data['is_file'],
            children=children,
            size=data.get('size'),
            modified_time=data.get('modified_time')
        )


class MerkleTree:
    """
    Merkle tree for tracking codebase changes.
    Enables efficient detection of modified files.
    """
    
    # Code files we want to index
    CODE_EXTENSIONS = {
        # Java
        '.java', '.kt', '.kts', '.groovy', '.scala',
        # C/C++
        '.c', '.h', '.cpp', '.hpp', '.cc', '.hh', '.cxx', '.hxx',
        '.C', '.H', '.CPP', '.HPP', '.tpp', '.txx',
        # Go
        '.go',
        # TypeScript/JavaScript
        '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
        # Python
        '.py', '.pyi', '.pyx', '.pxd', '.pxi',
        # Other common code files
        '.rs', '.rb', '.php', '.swift', '.m', '.mm',
        '.cs', '.fs', '.fsx', '.vb', '.r', '.dart',
        '.lua', '.pl', '.pm', '.t', '.pod', '.jl',
        '.ex', '.exs', '.erl', '.hrl', '.elm', '.clj',
        '.cljc', '.cljs', '.edn'
    }
    
    # Important files to index even without code extensions
    IMPORTANT_FILES = {
        'Dockerfile', 'Makefile', 'CMakeLists.txt',
        '.gitignore', '.dockerignore',
        'BUILD', 'WORKSPACE', '*.bzl',
        'pom.xml', 'build.gradle', 'settings.gradle',
        'Cargo.toml', 'go.mod', 'go.sum',
        'requirements.txt', 'setup.py', 'setup.cfg',
        'pyproject.toml', 'tox.ini', '.flake8',
        '.eslintrc*', '.prettierrc*', '.babelrc*',
        'webpack.config.js', 'rollup.config.js',
        'tsconfig.json', 'jsconfig.json'
    }
    
    # Directories to always ignore
    IGNORE_DIRS = {
        '.git', '.github', '__pycache__', 'node_modules', '.pytest_cache',
        'venv', 'env', '.venv', 'dist', 'build', 'target',
        'bin', 'obj', 'out', '.gradle', '.mvn', '.idea',
        '.vscode', '.vs', '.history', '.next', '.nuxt',
        '.output', '.cache', 'vendor', 'third_party',
        'third-party', '.bundle', 'eggs', '.eggs', 'lib',
        'lib64', 'parts', 'sdist', 'var', 'wheels',
        'share/python-wheels', '*.egg-info', '.installed.cfg',
        '*.egg', '.mypy_cache', '.pyre', '.pytype',
        'bower_components', 'jspm_packages', '.npm', '.yarn',
        '.settings', '.classpath', '.project', '.factorypath',
        '.recommenders', '.sts4-cache', 'pkg', 'pkg-mod',
        'mod', 'CMakeFiles', 'cmake-build-*', 'Debug',
        'Release', 'x64', 'x86', 'logs', 'tmp', 'temp',
        'coverage', '.nyc_output', '__snapshots__',
        '.serverless', '.terraform', '.env', '.env.*'
    }
    
    # Files to always ignore
    IGNORE_FILES = {
        # Package manager locks
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'poetry.lock', 'Cargo.lock', 'composer.lock',
        'Gemfile.lock', 'go.sum', 'Pipfile.lock',
        # Build outputs
        '*.min.js', '*.bundle.js', '*.chunk.js', '*.map',
        '*.d.ts.map', '*.js.map', '*.min.css',
        # Generated code
        '*.generated.*', '*.pb.go', '*.pb.cc', '*.pb.h',
        '*.grpc.pb.*', '*.thrift.*',
        # IDE/editor
        '*.iml', '*.iws', '*.ipr', '.classpath', '.project',
        '.settings/*', '*.sublime-*',
        # Large data files
        '*.sqlite', '*.db', '*.sql', '*.csv', '*.parquet',
        '*.avro', '*.orc', '*.feather', '*.pickle', '*.pkl',
        # Media files
        '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.svg',
        '*.mp4', '*.mp3', '*.webm', '*.wav', '*.ogg',
        # Fonts
        '*.woff', '*.woff2', '*.ttf', '*.eot',
        # Archives
        '*.zip', '*.tar', '*.gz', '*.bz2', '*.7z', '*.rar',
        '*.jar', '*.war', '*.ear', '*.nar',
        '*.dmg', '*.pkg', '*.deb', '*.rpm',
        '*.nupkg', '*.whl', '*.egg',
        # Binaries
        '*.exe', '*.dll', '*.so', '*.dylib', '*.o', '*.obj',
        '*.class', '*.pyo', '*.pyd', '*.pyc',
        '*.wasm', '*.wasm-decompile', '*.wasm.map',
        # Documentation
        '*.md', '*.txt', '*.rst', 'LICENSE*', 'COPYING*',
        'README*', 'CHANGELOG*', 'CONTRIBUTING*', 'CODE_OF_CONDUCT*',
        'SECURITY*', 'MAINTAINERS*', 'AUTHORS*',
        # OS files
        '.DS_Store', 'Thumbs.db', 'desktop.ini'
    }
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()
        self.root: Optional[MerkleNode] = None
        self.file_hashes: Dict[str, str] = {}
        
    def _hash_content(self, content: bytes) -> str:
        """Generate SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    def _hash_combine(self, hashes: List[str]) -> str:
        """Combine multiple hashes into one."""
        if not hashes:
            return hashlib.sha256(b"").hexdigest()
        combined = ''.join(sorted(hashes))
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _should_ignore(self, path: Path) -> bool:
        """
        Check if path should be ignored from code indexing.
        Returns True if path should be ignored.
        """
        # Never ignore the root directory
        if path == self.root_path:
            return False
            
        rel_path = path.relative_to(self.root_path) if path != self.root_path else path
        name = path.name
        path_str = str(path)
        
        # Check if directory should be ignored
        if path.is_dir():
            for pattern in self.IGNORE_DIRS:
                if '*' in pattern:
                    if any(fnmatch.fnmatch(part, pattern) for part in path.parts):
                        return True
                elif pattern in path.parts:
                    return True
            return False
        
        # For files: check if we should index them
        if path.is_file():
            # Check if file matches ignore patterns
            for pattern in self.IGNORE_FILES:
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(path_str, f'*{pattern}'):
                    return True
            
            # Check if it's a code file we want to index
            if path.suffix.lower() in self.CODE_EXTENSIONS:
                return False
            
            # Check if it's an important file we want to index
            if any(fnmatch.fnmatch(name, pattern) for pattern in self.IMPORTANT_FILES):
                return False
            
            # Otherwise ignore
            return True
        
        return False
    
    def build_tree(self, path: Optional[Path] = None) -> Optional[MerkleNode]:
        """
        Build Merkle tree from filesystem.
        
        Args:
            path: Path to build tree from (defaults to root_path)
            
        Returns:
            Root MerkleNode of the tree or None if should be ignored
        """
        if path is None:
            path = self.root_path
            
        # Check if path should be ignored
        if self._should_ignore(path):
            return None
            
        try:
            if path.is_file():
                content = path.read_bytes()
                file_hash = self._hash_content(content)
                
                # Store relative path for quick lookup
                try:
                    rel_path = str(path.relative_to(self.root_path))
                except ValueError:
                    rel_path = str(path)
                    
                self.file_hashes[rel_path] = file_hash
                
                # Get file metadata
                stat = path.stat()
                
                return MerkleNode(
                    path=rel_path,
                    hash=file_hash,
                    is_file=True,
                    size=stat.st_size,
                    modified_time=stat.st_mtime
                )
                
            elif path.is_dir():
                children = {}
                child_hashes = []
                
                # Iterate through directory contents
                for child_path in sorted(path.iterdir()):
                    child_node = self.build_tree(child_path)
                    if child_node:
                        children[child_path.name] = child_node
                        child_hashes.append(child_node.hash)
                
                # Skip empty directories
                if not children:
                    return None
                
                # Calculate directory hash from children
                dir_hash = self._hash_combine(child_hashes)
                
                # Get relative path
                if path == self.root_path:
                    rel_path = "."
                else:
                    try:
                        rel_path = str(path.relative_to(self.root_path))
                    except ValueError:
                        rel_path = str(path)
                
                return MerkleNode(
                    path=rel_path,
                    hash=dir_hash,
                    is_file=False,
                    children=children
                )
                
        except (PermissionError, OSError) as e:
            # Skip files/directories we can't access
            # print(f"Warning: Cannot access {path}: {e}")
            return None
        except Exception as e:
            print(f"Error processing {path}: {e}")
            return None
        
        return None
    
    def compare_trees(self, old_tree: MerkleNode, new_tree: MerkleNode) -> Dict[str, Set[str]]:
        """
        Compare two Merkle trees to find changes.
        
        Args:
            old_tree: Previous tree state
            new_tree: Current tree state
            
        Returns:
            Dict with 'added', 'modified', 'deleted' file sets
        """
        changes = {
            'added': set(),
            'modified': set(),
            'deleted': set(),
            'unchanged': set()
        }
        
        self._compare_nodes(old_tree, new_tree, changes)
        return changes
    
    def _compare_nodes(self, old_node: Optional[MerkleNode], 
                       new_node: Optional[MerkleNode], 
                       changes: Dict[str, Set[str]],
                       current_path: str = ""):
        """Recursively compare nodes to detect changes."""
        
        # Node deleted
        if old_node and not new_node:
            if old_node.is_file:
                changes['deleted'].add(old_node.path)
            else:
                self._collect_all_files(old_node, changes['deleted'])
            return
        
        # Node added
        if not old_node and new_node:
            if new_node.is_file:
                changes['added'].add(new_node.path)
            else:
                self._collect_all_files(new_node, changes['added'])
            return
        
        # Both exist
        if old_node and new_node:
            # Hash unchanged
            if old_node.hash == new_node.hash:
                if old_node.is_file:
                    changes['unchanged'].add(new_node.path)
                return
            
            # Hash changed
            if old_node.hash != new_node.hash:
                if old_node.is_file and new_node.is_file:
                    changes['modified'].add(new_node.path)
                elif not old_node.is_file and not new_node.is_file:
                    # Directory changed, recurse into children
                    old_children = old_node.children or {}
                    new_children = new_node.children or {}
                    
                    all_keys = set(old_children.keys()) | set(new_children.keys())
                    
                    for key in all_keys:
                        old_child = old_children.get(key)
                        new_child = new_children.get(key)
                        self._compare_nodes(old_child, new_child, changes)
    
    def _collect_all_files(self, node: MerkleNode, file_set: Set[str]):
        """Collect all file paths from a node and its children."""
        if node.is_file:
            file_set.add(node.path)
        elif node.children:
            for child in node.children.values():
                self._collect_all_files(child, file_set)
    
    def save_tree(self, filepath: Union[str, Path]):
        """Save tree to JSON file."""
        if self.root is None:
            raise ValueError("No tree built. Call build_tree() first.")
            
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'root': self.root.to_dict(),
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'root_path': str(self.root_path),
                'file_count': len(self.file_hashes)
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_tree(self, filepath: Union[str, Path]) -> MerkleNode:
        """Load tree from JSON file."""
        filepath = Path(filepath)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        # Handle both old format (direct node) and new format (with metadata)
        if 'root' in data:
            self.root = MerkleNode.from_dict(data['root'])
        else:
            self.root = MerkleNode.from_dict(data)
            
        return self.root
    
    def get_changed_files(self, old_tree_path: Union[str, Path]) -> Dict[str, Set[str]]:
        """
        Get changed files compared to a saved tree state.
        
        Args:
            old_tree_path: Path to saved tree JSON
            
        Returns:
            Dictionary of changes with 'added', 'modified', 'deleted', 'unchanged' sets
        """
        old_tree = self.load_tree(old_tree_path)
        self.root = self.build_tree()
        
        if self.root is None:
            raise ValueError("Failed to build new tree")
            
        return self.compare_trees(old_tree, self.root)
    
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Get hash for a specific file."""
        return self.file_hashes.get(file_path)
    
    def verify_file(self, file_path: str, expected_hash: str) -> bool:
        """Verify a file's hash matches expected value."""
        current_hash = self.get_file_hash(file_path)
        return current_hash == expected_hash