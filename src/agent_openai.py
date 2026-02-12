"""
AI Agent interface for codebase understanding with token optimization.
Demonstrates two-stage context loading: structure first, then selective code fetching.
Uses OpenAI SDK for easier integration.
"""
from typing import Dict, List, Optional
import json

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai not installed. Install with: pip install openai")

from indexer import CodebaseIndexer


class CodebaseAgent:
    """
    AI agent interface that uses indexed codebase for efficient LLM interactions.
    Implements token optimization through selective context loading.
    """
    
    def __init__(self, indexer: CodebaseIndexer, api_key: Optional[str] = None,
                 model: str = "gpt-4o-mini"):
        """
        Initialize codebase agent.
        
        Args:
            indexer: CodebaseIndexer instance
            api_key: OpenAI API key (optional, for demo)
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.indexer = indexer
        self.model = model
        
        if OPENAI_AVAILABLE and api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
        
        # Token counting
        self.token_stats = {
            'naive_approach': 0,  # Sending entire codebase
            'optimized_approach': 0,  # Using indexer
            'savings': 0
        }
    
    def answer_question(self, question: str, use_llm: bool = False) -> Dict:
        """
        Answer a question about the codebase with token optimization.
        
        Args:
            question: User's question about the code
            use_llm: Whether to actually call LLM (requires API key)
            
        Returns:
            Answer with token usage stats
        """
        print(f"\nQuestion: {question}")
        print("=" * 80)
        
        # Stage 1: Semantic search to find relevant code
        print("\nStage 1: Searching for relevant code...")
        relevant_entities = self.indexer.search_code(question, max_results=5)
        
        if not relevant_entities:
            return {
                'answer': 'No relevant code found for this question.',
                'relevant_entities': [],
                'token_stats': self.token_stats
            }
        
        print(f"   Found {len(relevant_entities)} relevant entities")
        for entity in relevant_entities:
            print(f"   - {entity['type']} {entity['name']} in {entity['file_path']}")
        
        # Stage 2: Build minimal context
        print("\nStage 2: Building minimal context...")
        context = self._build_minimal_context(relevant_entities)
        
        # Calculate token estimates
        self._estimate_tokens(context)
        
        # Prepare response
        response = {
            'question': question,
            'relevant_entities': [
                {
                    'name': e['name'],
                    'type': e['type'],
                    'file': e['file_path'],
                    'lines': f"{e['start_line']}-{e['end_line']}"
                }
                for e in relevant_entities
            ],
            'context': context,
            'token_stats': self.token_stats.copy()
        }
        
        # Optionally call LLM
        if use_llm and self.client:
            print("\n🤖 Stage 3: Querying LLM with optimized context...")
            answer = self._query_llm(question, context)
            response['answer'] = answer
        else:
            response['answer'] = "LLM query skipped (demo mode or no API key)"
        
        return response
    
    def _build_minimal_context(self, relevant_entities: List[Dict]) -> str:
        """
        Build minimal context from relevant entities.
        Only includes necessary code, not entire files.
        """
        context_parts = ["# Relevant Code Context\n"]
        
        for entity in relevant_entities:
            # Add entity header
            context_parts.append(f"\n## {entity['type'].title()}: {entity['name']}")
            context_parts.append(f"File: {entity['file_path']} (lines {entity['start_line']}-{entity['end_line']})")
            
            # Add dependencies context
            entity_context = self.indexer.get_entity_context(
                entity['name'],
                file_path=entity['file_path']
            )
            
            if entity_context.get('calls'):
                calls = [f"- {c['name']}" for c in entity_context['calls'][:3]]
                context_parts.append(f"Calls: {', '.join(calls[:3])}")
            
            if entity_context.get('called_by'):
                callers = [f"- {c['name']}" for c in entity_context['called_by'][:3]]
                context_parts.append(f"Called by: {', '.join(callers[:3])}")
            
            # Add code (already in search results)
            context_parts.append("\n```python")
            # Extract just the code part from the document
            code_lines = entity['code'].split('\n')
            # Skip metadata lines starting with #
            code = '\n'.join(line for line in code_lines if not line.startswith('#'))
            context_parts.append(code.strip())
            context_parts.append("```\n")
        
        return '\n'.join(context_parts)
    
    def _estimate_tokens(self, context: str):
        """
        Estimate token usage for naive vs optimized approach.
        Rough estimate: ~4 characters per token.
        """
        # Optimized: only relevant context
        optimized_tokens = len(context) // 4
        self.token_stats['optimized_approach'] = optimized_tokens
        
        # Naive: entire codebase
        total_chars = 0
        for file_path in self.indexer.indexed_files:
            full_path = self.indexer.codebase_path / file_path
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    total_chars += len(f.read())
            except:
                pass
        
        naive_tokens = total_chars // 4
        self.token_stats['naive_approach'] = naive_tokens
        self.token_stats['savings'] = naive_tokens - optimized_tokens
        self.token_stats['savings_percentage'] = (
            (self.token_stats['savings'] / naive_tokens * 100)
            if naive_tokens > 0 else 0
        )
        
        print(f"\n Token Usage Estimate:")
        print(f"   Naive approach (entire codebase): ~{naive_tokens:,} tokens")
        print(f"   Optimized approach (selective): ~{optimized_tokens:,} tokens")
        print(f"   Savings: ~{self.token_stats['savings']:,} tokens ({self.token_stats['savings_percentage']:.1f}%)")
    
    def _query_llm(self, question: str, context: str) -> str:
        """
        Query OpenAI LLM with optimized context.
        
        Args:
            question: User question
            context: Minimal context
            
        Returns:
            LLM response
        """
        system_prompt = """You are a code analysis assistant. Answer questions about codebases using the provided context.
        
Be concise and specific. Reference the actual code when explaining functionality."""

        user_prompt = f"""Context:
{context}

Question: {question}

Provide a clear, concise answer based on the code context provided."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error querying LLM: {e}"
    
    def analyze_file_change(self, file_path: str) -> Dict:
        """
        Analyze impact of changes to a file.
        
        Args:
            file_path: Path to changed file
            
        Returns:
            Impact analysis
        """
        print(f"\nAnalyzing impact of changes to: {file_path}")
        print("=" * 80)
        
        impact = self.indexer.get_impacted_by_change(file_path)
        
        print(f"\n Impact Summary:")
        print(f"   Total impacted entities: {impact['total_impacted_entities']}")
        print(f"   Impacted files: {impact['impacted_files']}")
        
        if impact['impacted_by_file']:
            print(f"\n  Impacted files:")
            for file, entities in list(impact['impacted_by_file'].items())[:5]:
                print(f"   {file}:")
                for entity in entities[:3]:
                    print(f"      - {entity}")
        
        return impact
    
    def get_project_summary(self) -> str:
        """
        Generate a summary of the codebase structure.
        This can be sent to LLM as high-level context before specific queries.
        """
        stats = self.indexer.get_statistics()
        
        summary_parts = [
            "# Codebase Summary\n",
            f"Total Files: {stats['metadata']['total_files']}",
            f"Total Entities: {stats['metadata']['total_entities']}",
            f"\n## Entity Distribution:",
        ]
        
        for entity_type, count in stats['call_graph']['entities_by_type'].items():
            summary_parts.append(f"- {entity_type.title()}s: {count}")
        
        summary_parts.append(f"\n## Key Statistics:")
        summary_parts.append(f"- Average calls per entity: {stats['call_graph']['avg_calls_per_entity']:.2f}")
        summary_parts.append(f"- Circular dependencies: {stats['call_graph']['circular_dependencies']}")
        
        # Add file structure overview
        summary_parts.append(f"\n## File Structure:")
        file_tree = self._build_file_tree()
        summary_parts.append(file_tree)
        
        return '\n'.join(summary_parts)
    
    def _build_file_tree(self, max_depth: int = 2) -> str:
        """Build a simple file tree visualization."""
        tree_lines = []
        files_by_dir = {}
        
        for file_path in sorted(self.indexer.indexed_files):
            parts = file_path.split('/')
            if len(parts) <= max_depth:
                dir_name = '/'.join(parts[:-1]) if len(parts) > 1 else '.'
                if dir_name not in files_by_dir:
                    files_by_dir[dir_name] = []
                files_by_dir[dir_name].append(parts[-1])
        
        for dir_name, files in sorted(files_by_dir.items()):
            tree_lines.append(f"{dir_name}/")
            for file in sorted(files)[:5]:  # Limit to 5 files per dir
                tree_lines.append(f"  - {file}")
            if len(files) > 5:
                tree_lines.append(f"  ... and {len(files) - 5} more")
        
        return '\n'.join(tree_lines)
    
    def demonstrate_token_optimization(self, sample_questions: List[str]):
        """
        Run demonstration showing token optimization across multiple questions.
        
        Args:
            sample_questions: List of questions to test
        """
        print("\n" + "=" * 80)
        print("TOKEN OPTIMIZATION DEMONSTRATION")
        print("=" * 80)
        
        total_naive = 0
        total_optimized = 0
        
        for i, question in enumerate(sample_questions, 1):
            print(f"\n\n{'='*80}")
            print(f"Example {i}/{len(sample_questions)}")
            result = self.answer_question(question, use_llm=False)
            
            total_naive += result['token_stats']['naive_approach']
            total_optimized += result['token_stats']['optimized_approach']
        
        # Final summary
        print("\n\n" + "=" * 80)
        print("OVERALL TOKEN SAVINGS SUMMARY")
        print("=" * 80)
        print(f"\nTotal queries: {len(sample_questions)}")
        print(f"Naive approach total: ~{total_naive:,} tokens")
        print(f"Optimized approach total: ~{total_optimized:,} tokens")
        print(f"Total savings: ~{total_naive - total_optimized:,} tokens")
        print(f"Average savings per query: {((total_naive - total_optimized) / len(sample_questions)):.0f} tokens")
        print(f"Percentage saved: {((total_naive - total_optimized) / total_naive * 100):.1f}%")
        
        # Cost comparison (using GPT-4o-mini pricing)
        input_cost_per_1m = 0.150  # $0.15 per 1M input tokens
        
        naive_cost = (total_naive / 1_000_000) * input_cost_per_1m
        optimized_cost = (total_optimized / 1_000_000) * input_cost_per_1m
        
        print(f"\n Cost Analysis (using gpt-4o-mini @ ${input_cost_per_1m}/1M tokens):")
        print(f"   Naive approach: ${naive_cost:.4f}")
        print(f"   Optimized approach: ${optimized_cost:.4f}")
        print(f"   Savings: ${naive_cost - optimized_cost:.4f}\n")
