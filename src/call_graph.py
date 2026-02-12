"""
Call graph and dependency relationship analyzer.
"""
import networkx as nx
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

from ast_parser import CodeEntity, CallReference


@dataclass
class DependencyInfo:
    """Information about code dependencies."""
    imports: List[str]
    file_path: str


class CallGraphAnalyzer:
    """
    Analyzes call graphs and dependency relationships in codebases.
    """
    
    def __init__(self):
        self.call_graph = nx.DiGraph()
        self.dependency_graph = nx.DiGraph()
        self.entities: Dict[str, CodeEntity] = {}
        self.file_entities: Dict[str, List[CodeEntity]] = {}
        
    def add_entity(self, entity: CodeEntity):
        """Add a code entity to the graph."""
        entity_id = f"{entity.file_path}::{entity.name}"
        self.entities[entity_id] = entity
        
        if entity.file_path not in self.file_entities:
            self.file_entities[entity.file_path] = []
        self.file_entities[entity.file_path].append(entity)
        
        # Add node to call graph
        self.call_graph.add_node(
            entity_id,
            name=entity.name,
            type=entity.type,
            file=entity.file_path,
            start_line=entity.start_line,
            end_line=entity.end_line
        )
    
    def add_call(self, call: CallReference):
        """Add a call reference to the graph."""
        caller_id = f"{call.file_path}::{call.caller}"
        callee_id = f"{call.file_path}::{call.callee}"
        
        if caller_id in self.entities and callee_id in self.entities:
            self.call_graph.add_edge(
                caller_id,
                callee_id,
                line=call.line_number
            )
    
    def add_file_dependency(self, from_file: str, to_file: str, import_type: str = "import"):
        """Add a file-level dependency."""
        self.dependency_graph.add_edge(from_file, to_file, type=import_type)
    
    def get_entity_dependencies(self, entity_id: str) -> Dict[str, List[str]]:
        """
        Get dependencies for an entity.
        
        Returns:
            Dict with 'calls' (what this calls) and 'called_by' (what calls this)
        """
        if entity_id not in self.call_graph:
            return {'calls': [], 'called_by': []}
        
        calls = list(self.call_graph.successors(entity_id))
        called_by = list(self.call_graph.predecessors(entity_id))
        
        return {
            'calls': calls,
            'called_by': called_by
        }
    
    def get_file_dependencies(self, file_path: str) -> Dict[str, List[str]]:
        """
        Get file-level dependencies.
        
        Returns:
            Dict with 'depends_on' and 'depended_by'
        """
        if file_path not in self.dependency_graph:
            return {'depends_on': [], 'depended_by': []}
        
        depends_on = list(self.dependency_graph.successors(file_path))
        depended_by = list(self.dependency_graph.predecessors(file_path))
        
        return {
            'depends_on': depends_on,
            'depended_by': depended_by
        }
    
    def get_call_chain(self, start_entity: str, end_entity: str) -> List[List[str]]:
        """
        Find all call paths from start to end entity.
        
        Args:
            start_entity: Starting entity ID
            end_entity: Target entity ID
            
        Returns:
            List of call paths
        """
        if start_entity not in self.call_graph or end_entity not in self.call_graph:
            return []
        
        try:
            paths = list(nx.all_simple_paths(
                self.call_graph,
                start_entity,
                end_entity,
                cutoff=10  # Limit depth to avoid infinite loops
            ))
            return paths
        except nx.NetworkXNoPath:
            return []
    
    def get_strongly_connected_components(self) -> List[Set[str]]:
        """
        Find strongly connected components (circular dependencies).
        
        Returns:
            List of entity sets with circular dependencies
        """
        return list(nx.strongly_connected_components(self.call_graph))
    
    def get_impacted_entities(self, changed_entity_id: str, max_depth: int = 3) -> Set[str]:
        """
        Get entities potentially impacted by changes to a given entity.
        
        Args:
            changed_entity_id: Entity that changed
            max_depth: Maximum dependency depth to consider
            
        Returns:
            Set of potentially impacted entity IDs
        """
        if changed_entity_id not in self.call_graph:
            return set()
        
        impacted = set()
        
        # BFS to find all callers up to max_depth
        visited = {changed_entity_id}
        queue = [(changed_entity_id, 0)]
        
        while queue:
            entity_id, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            # Get all entities that call this one
            callers = self.call_graph.predecessors(entity_id)
            
            for caller in callers:
                if caller not in visited:
                    visited.add(caller)
                    impacted.add(caller)
                    queue.append((caller, depth + 1))
        
        return impacted
    
    def get_entity_context(self, entity_id: str, include_calls: bool = True,
                          include_called_by: bool = True) -> Dict:
        """
        Get comprehensive context for an entity.
        
        Args:
            entity_id: Entity identifier
            include_calls: Include entities this calls
            include_called_by: Include entities that call this
            
        Returns:
            Dictionary with entity context
        """
        if entity_id not in self.entities:
            return {}
        
        entity = self.entities[entity_id]
        context = {
            'entity': {
                'name': entity.name,
                'type': entity.type,
                'file': entity.file_path,
                'lines': f"{entity.start_line}-{entity.end_line}",
                'parent_class': entity.parent_class
            }
        }
        
        if include_calls or include_called_by:
            deps = self.get_entity_dependencies(entity_id)
            
            if include_calls:
                context['calls'] = [
                    {
                        'name': self.entities[eid].name,
                        'file': self.entities[eid].file_path
                    }
                    for eid in deps['calls'] if eid in self.entities
                ]
            
            if include_called_by:
                context['called_by'] = [
                    {
                        'name': self.entities[eid].name,
                        'file': self.entities[eid].file_path
                    }
                    for eid in deps['called_by'] if eid in self.entities
                ]
        
        return context
    
    def export_graph(self, output_path: str):
        """Export call graph to JSON."""
        graph_data = {
            'entities': {
                entity_id: {
                    'name': entity.name,
                    'type': entity.type,
                    'file': entity.file_path,
                    'start_line': entity.start_line,
                    'end_line': entity.end_line,
                    'parent_class': entity.parent_class
                }
                for entity_id, entity in self.entities.items()
            },
            'calls': [
                {
                    'from': source,
                    'to': target,
                    'line': data.get('line')
                }
                for source, target, data in self.call_graph.edges(data=True)
            ],
            'file_dependencies': [
                {
                    'from': source,
                    'to': target,
                    'type': data.get('type')
                }
                for source, target, data in self.dependency_graph.edges(data=True)
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
    
    def get_statistics(self) -> Dict:
        """Get call graph statistics."""
        return {
            'total_entities': len(self.entities),
            'total_calls': self.call_graph.number_of_edges(),
            'total_files': len(self.file_entities),
            'entities_by_type': self._count_by_type(),
            'avg_calls_per_entity': (
                self.call_graph.number_of_edges() / len(self.entities)
                if len(self.entities) > 0 else 0
            ),
            'circular_dependencies': len([
                comp for comp in self.get_strongly_connected_components()
                if len(comp) > 1
            ])
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count entities by type."""
        counts = {}
        for entity in self.entities.values():
            counts[entity.type] = counts.get(entity.type, 0) + 1
        return counts
