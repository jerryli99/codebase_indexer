__version__ = "1.0.0"
__author__ = "Jerry Li"

from .merkle_tree import MerkleTree, MerkleNode
from .ast_parser import ASTParser, CodeEntity, CallReference
from .call_graph import CallGraphAnalyzer
from .embeddings import CodeEmbeddingManager
from .indexer import CodebaseIndexer

#might add agent here

__all__ = [
    'MerkleTree',
    'MerkleNode',
    'ASTParser',
    'CodeEntity',
    'CallReference',
    'CallGraphAnalyzer',
    'CodeEmbeddingManager',
    'CodebaseIndexer',
]