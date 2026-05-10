"""
Hybrid Context Formatter

Merges aider's tree‑sitter repo map with Testeranto's GraphQL context.

The formatter:
1. Computes the tree‑sitter repo map (fast, local)
2. Queries GraphQL for global context (entrypoints, AST deps, test results, agent data)
3. Merges both into virtual files
4. Returns formatted context for the LLM
"""

import json
from typing import Any, Dict, List, Optional

from aider.graphql_client import GraphQLClient


class HybridContextFormatter:
    """Merges tree‑sitter repo map with GraphQL context."""

    def __init__(
        self,
        graphql_client: Optional[GraphQLClient] = None,
        agent_name: Optional[str] = None,
        current_file: Optional[str] = None,
        current_test: Optional[str] = None,
    ):
        self.graphql = graphql_client or GraphQLClient()
        self.agent_name = agent_name or "aider"
        self.current_file = current_file
        self.current_test = current_test

    def format_context(self, repo_map: Optional[str] = None) -> str:
        """
        Build the context for the next LLM call.

        Args:
            repo_map: Optional pre-computed tree‑sitter repo map string.
                      If None, only GraphQL context is used.

        Returns:
            Formatted context string with both sources merged.
        """
        context_parts = []

        # 1. tree‑sitter repo map (fast, local)
        if repo_map:
            context_parts.append(
                f"## Repo Map (tree‑sitter)\n\n{repo_map}\n"
            )

        # 2. GraphQL query (accurate, global)
        graph_context = self._fetch_graph_context()
        if graph_context:
            context_parts.append(
                f"## Graph Context (Testeranto)\n\n{graph_context}\n"
            )

        return "\n".join(context_parts)

    def _fetch_graph_context(self) -> Optional[str]:
        """Fetch global context from GraphQL."""
        try:
            # Build the GraphQL query with available parameters
            query_parts = []

            # Entrypoints
            query_parts.append("entrypoints { path runtime }")

            # AST dependencies for current file
            if self.current_file:
                query_parts.append(
                    f'astDeps(entrypoint: "{self.current_file}") {{ files }}'
                )

            # Test results for current test
            if self.current_test:
                query_parts.append(
                    f'testResults(test: "{self.current_test}") {{ status }}'
                )

            # Agent context
            if self.agent_name:
                query_parts.append(
                    f'agentContext(agent: "{self.agent_name}") {{ files }}'
                )

            if not query_parts:
                return None

            query = f"query {{ {' '.join(query_parts)} }}"
            data = self.graphql._execute(query)

            # Format the result as readable text
            lines = []
            for key, value in data.items():
                if value:
                    lines.append(f"### {key}")
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                lines.append(f"- {json.dumps(item)}")
                            else:
                                lines.append(f"- {item}")
                    elif isinstance(value, dict):
                        lines.append(json.dumps(value, indent=2))
                    else:
                        lines.append(str(value))
                    lines.append("")

            return "\n".join(lines) if lines else None

        except Exception as e:
            # GraphQL is optional; if it fails, we just skip it
            return f"## GraphQL context unavailable: {e}"

    def create_virtual_file_for_context(
        self,
        name: str,
        content: str,
        source: str,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Store context as a virtual file in the graph.

        Args:
            name: Virtual file name (e.g., "repo-map", "graph-context")
            content: The context content
            source: Source type ("tree-sitter" or "graphql")
            ttl: Time-to-live in seconds (default: None = permanent)

        Returns:
            Virtual file metadata from the GraphQL response.
        """
        return self.graphql.create_virtual_file(
            name=name,
            content=content,
            source=source,
            ttl=ttl,
            created_by=self.agent_name,
        )

    def get_virtual_files_in_context(self) -> List[Dict[str, Any]]:
        """Get all virtual files currently marked as in-context."""
        return self.graphql.get_virtual_files(in_context=True)

    def set_file_context(self, name: str, in_context: bool) -> Dict[str, Any]:
        """Set whether a virtual file is included in aider's context."""
        return self.graphql.set_virtual_file_context(name, in_context)
"""
Hybrid Context Formatter

Merges aider's tree‑sitter repo map with Testeranto's GraphQL context.

The formatter:
1. Computes the tree‑sitter repo map (fast, local)
2. Queries GraphQL for global context (entrypoints, AST deps, test results, agent data)
3. Merges both into virtual files
4. Returns formatted context for the LLM
"""

import json
from typing import Any, Dict, List, Optional

from aider.graphql_client import GraphQLClient


class HybridContextFormatter:
    """Merges tree‑sitter repo map with GraphQL context."""

    def __init__(
        self,
        graphql_client: Optional[GraphQLClient] = None,
        agent_name: Optional[str] = None,
        current_file: Optional[str] = None,
        current_test: Optional[str] = None,
    ):
        self.graphql = graphql_client or GraphQLClient()
        self.agent_name = agent_name or "aider"
        self.current_file = current_file
        self.current_test = current_test

    def format_context(self, repo_map: Optional[str] = None) -> str:
        """
        Build the context for the next LLM call.

        Args:
            repo_map: Optional pre-computed tree‑sitter repo map string.
                      If None, only GraphQL context is used.

        Returns:
            Formatted context string with both sources merged.
        """
        context_parts = []

        # 1. tree‑sitter repo map (fast, local)
        if repo_map:
            context_parts.append(
                f"## Repo Map (tree‑sitter)\n\n{repo_map}\n"
            )

        # 2. GraphQL query (accurate, global)
        graph_context = self._fetch_graph_context()
        if graph_context:
            context_parts.append(
                f"## Graph Context (Testeranto)\n\n{graph_context}\n"
            )

        return "\n".join(context_parts)

    def _fetch_graph_context(self) -> Optional[str]:
        """Fetch global context from GraphQL."""
        try:
            # Build the GraphQL query with available parameters
            query_parts = []

            # Entrypoints
            query_parts.append("entrypoints { path runtime }")

            # AST dependencies for current file
            if self.current_file:
                query_parts.append(
                    f'astDeps(entrypoint: "{self.current_file}") {{ files }}'
                )

            # Test results for current test
            if self.current_test:
                query_parts.append(
                    f'testResults(test: "{self.current_test}") {{ status }}'
                )

            # Agent context
            if self.agent_name:
                query_parts.append(
                    f'agentContext(agent: "{self.agent_name}") {{ files }}'
                )

            if not query_parts:
                return None

            query = f"query {{ {' '.join(query_parts)} }}"
            data = self.graphql._execute(query)

            # Format the result as readable text
            lines = []
            for key, value in data.items():
                if value:
                    lines.append(f"### {key}")
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                lines.append(f"- {json.dumps(item)}")
                            else:
                                lines.append(f"- {item}")
                    elif isinstance(value, dict):
                        lines.append(json.dumps(value, indent=2))
                    else:
                        lines.append(str(value))
                    lines.append("")

            return "\n".join(lines) if lines else None

        except Exception as e:
            # GraphQL is optional; if it fails, we just skip it
            return f"## GraphQL context unavailable: {e}"

    def create_virtual_file_for_context(
        self,
        name: str,
        content: str,
        source: str,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Store context as a virtual file in the graph.

        Args:
            name: Virtual file name (e.g., "repo-map", "graph-context")
            content: The context content
            source: Source type ("tree-sitter" or "graphql")
            ttl: Time-to-live in seconds (default: None = permanent)

        Returns:
            Virtual file metadata from the GraphQL response.
        """
        return self.graphql.create_virtual_file(
            name=name,
            content=content,
            source=source,
            ttl=ttl,
            created_by=self.agent_name,
        )

    def get_virtual_files_in_context(self) -> List[Dict[str, Any]]:
        """Get all virtual files currently marked as in-context."""
        return self.graphql.get_virtual_files(in_context=True)

    def set_file_context(self, name: str, in_context: bool) -> Dict[str, Any]:
        """Set whether a virtual file is included in aider's context."""
        return self.graphql.set_virtual_file_context(name, in_context)
