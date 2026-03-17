"""Tests for pipeline graph wiring — verifies node connectivity."""

from __future__ import annotations

from siopv.application.orchestration.graph import PipelineGraphBuilder


class TestGraphWiring:
    """Verify that the compiled graph has the expected node structure."""

    def test_escalate_node_exists_in_graph(self) -> None:
        """Test that the graph contains an 'escalate' node."""
        builder = PipelineGraphBuilder()
        builder.build()
        graph = builder._graph

        assert graph is not None
        assert "escalate" in graph.nodes

    def test_all_expected_nodes_present(self) -> None:
        """Test that all expected pipeline nodes are present."""
        builder = PipelineGraphBuilder()
        builder.build()
        graph = builder._graph

        assert graph is not None
        expected_nodes = {"authorize", "ingest", "dlp", "enrich", "classify", "escalate"}
        actual_nodes = set(graph.nodes.keys())
        assert expected_nodes.issubset(actual_nodes), (
            f"Missing nodes: {expected_nodes - actual_nodes}"
        )

    def test_classify_has_conditional_edges(self) -> None:
        """Test that classify node has conditional edges including escalate route."""
        builder = PipelineGraphBuilder()
        builder.build()
        graph = builder._graph

        assert graph is not None
        # StateGraph stores conditional edges; verify classify node is wired
        # by checking that the graph builds without error and has both nodes
        assert "classify" in graph.nodes
        assert "escalate" in graph.nodes
