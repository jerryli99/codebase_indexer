"""
AST parsing and analysis using tree-sitter for multiple programming languages.
Compatible with tree-sitter 0.25+
"""
from tree_sitter import Language, Parser, Tree, Node
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
import importlib
import sys


@dataclass
class CodeEntity:
    """Represents a code entity (function, class, method)."""
    name: str
    type: str  # 'function', 'class', 'method', 'constructor', 'struct', 'interface'
    start_line: int
    end_line: int
    file_path: str
    signature: Optional[str] = None
    parent_class: Optional[str] = None
    docstring: Optional[str] = None


@dataclass
class CallReference:
    """Represents a function/method call."""
    caller: str  # caller entity name
    callee: str  # called entity name
    file_path: str
    line_number: int


class ASTParser:
    """
    Multi-language AST parser using tree-sitter.
    Supports Python, JavaScript/TypeScript, Java, C, and Go.
    Fully compatible with tree-sitter 0.25+
    """
    
    # Language-specific query patterns (tree-sitter 0.25 compatible)
    QUERIES = {
        'python': """
            (function_definition
                name: (identifier) @function.name
                parameters: (parameters) @function.params
                body: (block) @function.body) @function.def
            
            (class_definition
                name: (identifier) @class.name
                body: (block) @class.body) @class.def
            
            (call
                function: (identifier) @call.name) @call
        """,
        
        'javascript': """
            (function_declaration
                name: (identifier) @function.name
                parameters: (formal_parameters) @function.params
                body: (statement_block) @function.body) @function.def
            
            (class_declaration
                name: (type_identifier) @class.name
                body: (class_body) @class.body) @class.def
            
            (method_definition
                name: (property_identifier) @method.name
                parameters: (formal_parameters) @method.params
                body: (statement_block) @method.body) @method.def
        """,
        
        'java': """
            (method_declaration
                name: (identifier) @method.name
                parameters: (formal_parameters) @method.params
                body: (block) @method.body) @method.def
            
            (class_declaration
                name: (identifier) @class.name
                body: (class_body) @class.body) @class.def
            
            (constructor_declaration
                name: (identifier) @constructor.name
                parameters: (formal_parameters) @constructor.params
                body: (block) @constructor.body) @constructor.def
        """,
        
        'c': """
            (function_definition
                declarator: (function_declarator
                    declarator: (identifier) @function.name
                    parameters: (parameter_list) @function.params)
                body: (compound_statement) @function.body) @function.def
            
            (function_definition
                declarator: (pointer_declarator
                    declarator: (function_declarator
                        declarator: (identifier) @function.name
                        parameters: (parameter_list) @function.params))
                body: (compound_statement) @function.body) @function.def
            
            (call_expression
                function: (identifier) @call.name) @call
            
            (struct_specifier
                name: (type_identifier) @struct.name) @struct.def
        """,
        
        'go': """
            (function_declaration
                name: (identifier) @function.name
                parameters: (parameter_list) @function.params
                result: (_)? @function.result
                body: (block) @function.body) @function.def
            
            (method_declaration
                name: (field_identifier) @method.name
                parameters: (parameter_list) @method.params
                result: (_)? @method.result
                body: (block) @method.body) @method.def
            
            (struct_type) @struct.def
            (interface_type) @interface.def
        """
    }
    
    def __init__(self, debug: bool = False):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}
        self.debug = debug
        self._init_languages()
    
    def _init_languages(self):
        """Initialize tree-sitter parsers for supported languages."""
        # Language extensions mapping
        self.lang_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'javascript',
            '.jsx': 'javascript',
            '.tsx': 'javascript',
            '.java': 'java',
            '.c': 'c',
            '.h': 'c',
            '.go': 'go'
        }
        
        # Map of language names to import modules
        language_imports = {
            'python': 'tree_sitter_python',
            'javascript': 'tree_sitter_javascript',
            'java': 'tree_sitter_java',
            'c': 'tree_sitter_c',
            'go': 'tree_sitter_go'
        }
        
        try:
            from tree_sitter import Language, Parser
            
            for lang_name, module_name in language_imports.items():
                try:
                    # Dynamically import the language module
                    lang_module = __import__(module_name)
                    
                    # Get the language object
                    lang = Language(lang_module.language())
                    
                    # Store language and create parser
                    self.languages[lang_name] = lang
                    parser = Parser()
                    
                    # ⚠️ FIX: Use attribute assignment, not set_language()
                    parser.language = lang
                    
                    self.parsers[lang_name] = parser
                    
                    print(f"✓ Loaded {lang_name} parser")
                    
                except ImportError:
                    print(f"  ✗ {lang_name} not installed. Install with: pip install {module_name}")
                except Exception as e:
                    print(f"  ✗ Error loading {lang_name}: {e}")
                    
        except ImportError:
            print("Warning: tree_sitter not installed. Please install with: pip install tree-sitter")
    
    def _get_language(self, file_path: str) -> Optional[str]:
        """Determine language from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.lang_extensions.get(ext)
    
    def parse_file(self, file_path: str) -> Optional[Tree]:
        """
        Parse a source file into AST.
        
        Args:
            file_path: Path to source file
            
        Returns:
            Tree-sitter Tree object or None
        """
        lang = self._get_language(file_path)
        if not lang:
            return None
        
        # Handle TypeScript with JavaScript parser if TypeScript not available
        if lang == 'typescript' and 'typescript' not in self.parsers:
            if 'javascript' in self.parsers:
                lang = 'javascript'
            else:
                return None
        
        if lang not in self.parsers:
            return None
        
        try:
            with open(file_path, 'rb') as f:
                code = f.read()
            
            parser = self.parsers[lang]
            tree = parser.parse(code)
            return tree
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def extract_entities(self, file_path: str) -> List[CodeEntity]:
        """
        Extract code entities (functions, classes, methods) from file.
        
        Args:
            file_path: Path to source file
            
        Returns:
            List of CodeEntity objects
        """
        tree = self.parse_file(file_path)
        if not tree:
            return []
        
        lang = self._get_language(file_path)
        entities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_lines = f.readlines()
        except Exception:
            return []
        
        # Use both query-based and traversal-based extraction for best results
        self._extract_with_queries(tree.root_node, lang, file_path, entities, code_lines)
        self._extract_from_node(tree.root_node, file_path, entities, code_lines)
        
        # Deduplicate entities (keep last occurrence)
        unique_entities = {}
        for entity in entities:
            key = (entity.name, entity.type, entity.start_line)
            unique_entities[key] = entity
        
        return list(unique_entities.values())
    
    def _extract_with_queries(self, root_node: Node, lang: str, file_path: str, 
                            entities: List[CodeEntity], code_lines: List[str]):
        """Extract entities using tree-sitter queries (compatible with older tree-sitter)."""
        if lang not in self.QUERIES:
            return
        
        try:
            # Create query
            query = self.languages[lang].query(self.QUERIES[lang])
            
            # OLD API: query.captures(node) returns list of (node, capture_name)
            captures = query.captures(root_node)
            
            # Process captures - handle both old and new API formats
            for item in captures:
                # Old API: each item is a tuple (node, capture_name)
                if isinstance(item, tuple) and len(item) == 2:
                    node, capture_name = item
                # New API: might be different format
                elif hasattr(item, 'node') and hasattr(item, 'name'):
                    node, capture_name = item.node, item.name
                else:
                    continue
                
                if capture_name in ['function.name', 'method.name', 'constructor.name', 
                                'class.name', 'struct.name', 'interface.name']:
                    name = self._get_node_text(node, code_lines)
                    
                    # Find parent definition node
                    parent = node.parent
                    while parent and not parent.type.endswith('_definition') and \
                        not parent.type.endswith('_specifier') and \
                        parent.type not in ['struct_type', 'interface_type']:
                        parent = parent.parent
                    
                    if parent:
                        # Determine entity type
                        if 'function' in capture_name:
                            entity_type = 'function'
                        elif 'method' in capture_name:
                            entity_type = 'method'
                        elif 'constructor' in capture_name:
                            entity_type = 'constructor'
                        elif 'class' in capture_name:
                            entity_type = 'class'
                        elif 'struct' in capture_name:
                            entity_type = 'struct'
                        elif 'interface' in capture_name:
                            entity_type = 'interface'
                        else:
                            entity_type = 'unknown'
                        
                        entity = CodeEntity(
                            name=name,
                            type=entity_type,
                            start_line=parent.start_point[0] + 1,
                            end_line=parent.end_point[0] + 1,
                            file_path=file_path
                        )
                        entities.append(entity)
                        
        except Exception as e:
            if self.debug:
                print(f"Query extraction error for {lang}: {e}")
    
    def _extract_from_node(self, node: Node, file_path: str, entities: List[CodeEntity], 
                           code_lines: List[str], parent_class: Optional[str] = None):
        """Recursively extract entities from AST node."""
        
        # Python
        if node.type == 'function_definition':
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=name,
                    type='method' if parent_class else 'function',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    parent_class=parent_class
                )
                entities.append(entity)
        
        elif node.type == 'class_definition':
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                class_name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=class_name,
                    type='class',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path
                )
                entities.append(entity)
                
                # Process class body with class context
                for child in node.children:
                    self._extract_from_node(child, file_path, entities, code_lines, class_name)
                return
        
        # JavaScript/TypeScript
        elif node.type in ['function_declaration', 'function']:
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                name = self._get_node_text(name_node, code_lines)
            else:
                name = f"anonymous_{node.start_point[0] + 1}"
            
            entity = CodeEntity(
                name=name,
                type='method' if parent_class else 'function',
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                file_path=file_path,
                parent_class=parent_class
            )
            entities.append(entity)
        
        elif node.type == 'class_declaration':
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                class_name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=class_name,
                    type='class',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path
                )
                entities.append(entity)
                
                for child in node.children:
                    self._extract_from_node(child, file_path, entities, code_lines, class_name)
                return
        
        elif node.type == 'method_definition':
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=name,
                    type='method',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    parent_class=parent_class
                )
                entities.append(entity)
        
        # Java
        elif node.type == 'method_declaration':
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=name,
                    type='method',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    parent_class=parent_class
                )
                entities.append(entity)
        
        elif node.type == 'class_declaration':
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                class_name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=class_name,
                    type='class',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path
                )
                entities.append(entity)
                
                for child in node.children:
                    self._extract_from_node(child, file_path, entities, code_lines, class_name)
                return
        
        elif node.type == 'constructor_declaration':
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=name,
                    type='constructor',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    parent_class=parent_class
                )
                entities.append(entity)
        
        # C - FIXED for tree-sitter-c 0.25+
        elif node.type == 'function_definition':
            declarator = node.child_by_field_name('declarator')
            if declarator:
                # Handle direct function declarator
                if declarator.type == 'function_declarator':
                    name_node = declarator.child_by_field_name('declarator')
                    if name_node and name_node.type == 'identifier':
                        name = self._get_node_text(name_node, code_lines)
                        entity = CodeEntity(
                            name=name,
                            type='function',
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            file_path=file_path
                        )
                        entities.append(entity)
                
                # Handle pointer function declarator (int *function())
                elif declarator.type == 'pointer_declarator':
                    inner = declarator.child_by_field_name('declarator')
                    if inner and inner.type == 'function_declarator':
                        name_node = inner.child_by_field_name('declarator')
                        if name_node and name_node.type == 'identifier':
                            name = self._get_node_text(name_node, code_lines)
                            entity = CodeEntity(
                                name=name,
                                type='function',
                                start_line=node.start_point[0] + 1,
                                end_line=node.end_point[0] + 1,
                                file_path=file_path
                            )
                            entities.append(entity)
        
        elif node.type == 'struct_specifier':
            name_node = node.child_by_field_name('name')
            if name_node and name_node.type == 'type_identifier':
                name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=name,
                    type='struct',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path
                )
                entities.append(entity)
        
        # Go
        elif node.type == 'function_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = self._get_node_text(name_node, code_lines)
                entity = CodeEntity(
                    name=name,
                    type='function',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path
                )
                entities.append(entity)
        
        elif node.type == 'method_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                name = self._get_node_text(name_node, code_lines)
                
                # Get receiver for Go methods
                receiver = node.child_by_field_name('receiver')
                receiver_type = None
                if receiver:
                    for child in receiver.children:
                        if child.type in ['type_identifier', 'identifier']:
                            receiver_type = self._get_node_text(child, code_lines)
                            break
                
                entity = CodeEntity(
                    name=name,
                    type='method',
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    parent_class=receiver_type
                )
                entities.append(entity)
        
        elif node.type == 'struct_type':
            parent = node.parent
            if parent and parent.type == 'type_spec':
                name_node = parent.child_by_field_name('name')
                if name_node:
                    struct_name = self._get_node_text(name_node, code_lines)
                    entity = CodeEntity(
                        name=struct_name,
                        type='struct',
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        file_path=file_path
                    )
                    entities.append(entity)
        
        elif node.type == 'interface_type':
            parent = node.parent
            if parent and parent.type == 'type_spec':
                name_node = parent.child_by_field_name('name')
                if name_node:
                    interface_name = self._get_node_text(name_node, code_lines)
                    entity = CodeEntity(
                        name=interface_name,
                        type='interface',
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        file_path=file_path
                    )
                    entities.append(entity)
        
        # Recurse into children
        for child in node.children:
            self._extract_from_node(child, file_path, entities, code_lines, parent_class)
    
    def _get_child_by_field(self, node: Node, field_name: str) -> Optional[Node]:
        """Find child node by field name (tree-sitter 0.25+)."""
        try:
            # tree-sitter 0.25+ API
            return node.child_by_field_name(field_name)
        except Exception:
            # Fallback for older versions
            for child in node.children:
                if child.type in ['identifier', 'type_identifier', 'field_identifier', 
                                 'property_identifier']:
                    return child
        return None
    
    def _get_node_text(self, node: Node, code_lines: List[str]) -> str:
        """Extract text from node."""
        start_line = node.start_point[0]
        start_col = node.start_point[1]
        end_line = node.end_point[0]
        end_col = node.end_point[1]
        
        if start_line == end_line:
            return code_lines[start_line][start_col:end_col].strip()
        else:
            text = code_lines[start_line][start_col:]
            for i in range(start_line + 1, end_line):
                text += code_lines[i]
            text += code_lines[end_line][:end_col]
            return text.strip()
    
    def extract_calls(self, file_path: str, entities: List[CodeEntity]) -> List[CallReference]:
        """
        Extract function/method calls from file.
        
        Args:
            file_path: Path to source file
            entities: List of entities in the file
            
        Returns:
            List of CallReference objects
        """
        tree = self.parse_file(file_path)
        if not tree:
            return []
        
        calls = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_lines = f.readlines()
        except Exception:
            return []
        
        # Build entity map for quick lookup
        entity_map = {e.name: e for e in entities}
        
        # Extract calls
        self._extract_calls_from_node(tree.root_node, file_path, calls, 
                                     code_lines, entity_map)
        
        return calls
    
    def _extract_calls_from_node(self, node: Node, file_path: str, calls: List[CallReference],
                                 code_lines: List[str], entity_map: Dict[str, CodeEntity],
                                 current_entity: Optional[str] = None):
        """Recursively extract call references from AST node."""
        
        # Track current function context
        if node.type in ['function_definition', 'function_declaration', 
                         'method_declaration', 'method_definition', 
                         'constructor_declaration']:
            name_node = self._get_child_by_field(node, 'name')
            if name_node:
                current_entity = self._get_node_text(name_node, code_lines)
        
        # C function definitions
        elif node.type == 'function_definition':
            declarator = node.child_by_field_name('declarator')
            if declarator:
                if declarator.type == 'function_declarator':
                    name_node = declarator.child_by_field_name('declarator')
                    if name_node:
                        current_entity = self._get_node_text(name_node, code_lines)
                elif declarator.type == 'pointer_declarator':
                    inner = declarator.child_by_field_name('declarator')
                    if inner and inner.type == 'function_declarator':
                        name_node = inner.child_by_field_name('declarator')
                        if name_node:
                            current_entity = self._get_node_text(name_node, code_lines)
        
        # Detect call expressions
        call_types = ['call', 'call_expression', 'method_invocation']
        
        if node.type in call_types:
            callee_name = None
            
            # Python/JavaScript calls
            if node.type in ['call', 'call_expression']:
                function_node = node.child_by_field_name('function')
                if function_node:
                    callee_name = self._get_node_text(function_node, code_lines)
            
            # Java method invocations
            elif node.type == 'method_invocation':
                name_node = self._get_child_by_field(node, 'name')
                if name_node:
                    callee_name = self._get_node_text(name_node, code_lines)
            
            # Create call reference if we have both caller and callee
            if current_entity and callee_name:
                # Try exact match
                if callee_name in entity_map:
                    call = CallReference(
                        caller=current_entity,
                        callee=callee_name,
                        file_path=file_path,
                        line_number=node.start_point[0] + 1
                    )
                    calls.append(call)
                else:
                    # Try simple name (for qualified names)
                    simple_name = callee_name.split('.')[-1]
                    if simple_name in entity_map:
                        call = CallReference(
                            caller=current_entity,
                            callee=simple_name,
                            file_path=file_path,
                            line_number=node.start_point[0] + 1
                        )
                        calls.append(call)
        
        # Recurse
        for child in node.children:
            self._extract_calls_from_node(child, file_path, calls, code_lines, 
                                         entity_map, current_entity)
    
    def get_language_stats(self) -> Dict[str, int]:
        """Get statistics about parsed languages."""
        stats = {
            'python': 0,
            'javascript': 0,
            'typescript': 0,
            'java': 0,
            'c': 0,
            'go': 0
        }
        
        for parser_name in self.parsers:
            if parser_name in stats:
                stats[parser_name] = 1
        
        return stats