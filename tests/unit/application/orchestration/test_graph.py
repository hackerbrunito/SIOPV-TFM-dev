"""Tests for LangGraph pipeline builder."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from siopv.application.orchestration.graph import (
    PipelineGraphBuilder,
    PipelinePorts,
    create_pipeline_graph,
    run_pipeline,
)
from siopv.application.orchestration.state import create_initial_state


class TestPipelineGraphBuilder:
    """Tests for PipelineGraphBuilder class."""

    def test_builder_initialization(self):
        """Test builder initializes with defaults."""
        builder = PipelineGraphBuilder()

        assert builder._ports.checkpoint_db_path is None
        assert builder._graph is None
        assert builder._compiled is None

    def test_builder_with_custom_checkpoint_path(self):
        """Test builder with custom checkpoint path."""
        ports = PipelinePorts(checkpoint_db_path="/custom/path.db")
        builder = PipelineGraphBuilder(ports)

        assert builder._ports.checkpoint_db_path == "/custom/path.db"

    def test_build_returns_self(self):
        """Test build() returns self for chaining."""
        builder = PipelineGraphBuilder()

        result = builder.build()

        assert result is builder
        assert builder._graph is not None

    def test_compile_without_checkpointer(self):
        """Test compiling without checkpointer."""
        builder = PipelineGraphBuilder()

        compiled = builder.build().compile(with_checkpointer=False)

        assert compiled is not None

    def test_compile_with_checkpointer(self):
        """Test compiling with SQLite checkpointer."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        ports = PipelinePorts(checkpoint_db_path=db_path)
        builder = PipelineGraphBuilder(ports)

        compiled = builder.build().compile(with_checkpointer=True)

        assert compiled is not None

    def test_get_compiled_auto_builds(self):
        """Test get_compiled() builds and compiles if needed."""
        builder = PipelineGraphBuilder()

        compiled = builder.get_compiled()

        assert compiled is not None
        assert builder._compiled is not None

    def test_visualize_generates_mermaid(self):
        """Test visualization generates Mermaid diagram."""
        builder = PipelineGraphBuilder()
        builder.build().compile(with_checkpointer=False)

        mermaid = builder.visualize()

        assert isinstance(mermaid, str)
        assert "ingest" in mermaid.lower() or "graph" in mermaid.lower()

    def test_save_visualization(self):
        """Test saving visualization to file."""
        builder = PipelineGraphBuilder()
        builder.build().compile(with_checkpointer=False)

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            output_path = Path(f.name)

        result_path = builder.save_visualization(output_path)

        # Compare resolved paths (handles symlinks like /var -> /private/var on macOS)
        assert result_path.resolve() == output_path.resolve()
        assert output_path.exists()
        content = output_path.read_text()
        assert len(content) > 0


class TestCreatePipelineGraph:
    """Tests for create_pipeline_graph factory function."""

    def test_creates_compiled_graph(self):
        """Test factory creates compiled graph."""
        graph = create_pipeline_graph(with_checkpointer=False)

        assert graph is not None

    def test_with_custom_checkpoint_path(self):
        """Test factory with custom checkpoint path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        ports = PipelinePorts(checkpoint_db_path=db_path)
        graph = create_pipeline_graph(
            ports,
            with_checkpointer=True,
        )

        assert graph is not None


class TestRunPipeline:
    """Tests for run_pipeline convenience function."""

    @pytest.fixture
    def sample_trivy_report(self) -> dict:
        """Create a sample Trivy report."""
        return {
            "SchemaVersion": 2,
            "ArtifactName": "test-image:latest",
            "Results": [
                {
                    "Target": "test-image",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-1234",
                            "PkgName": "openssl",
                            "InstalledVersion": "1.1.1",
                            "Severity": "HIGH",
                        }
                    ],
                }
            ],
        }

    @pytest.fixture
    def trivy_report_file(self, sample_trivy_report: dict) -> Path:
        """Create a temporary Trivy report file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_trivy_report, f)
            return Path(f.name)

    async def test_run_pipeline_basic(self, trivy_report_file: Path):
        """Test basic pipeline execution."""
        result = await run_pipeline(trivy_report_file)

        assert "vulnerabilities" in result
        assert "enrichments" in result
        assert "classifications" in result
        assert "escalated_cves" in result
        assert "thread_id" in result

    async def test_run_pipeline_with_thread_id(self, trivy_report_file: Path):
        """Test pipeline with custom thread ID."""
        result = await run_pipeline(
            trivy_report_file,
            thread_id="custom-thread-123",
        )

        assert result["thread_id"] == "custom-thread-123"

    async def test_run_pipeline_with_checkpoint(self, trivy_report_file: Path):
        """Test pipeline with checkpointing enabled."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        ports = PipelinePorts(checkpoint_db_path=db_path)
        result = await run_pipeline(
            trivy_report_file,
            ports,
        )

        assert result is not None
        assert Path(db_path).exists()


class TestGraphStructure:
    """Tests for graph structure and routing."""

    def test_graph_has_expected_nodes(self):
        """Test graph contains all expected nodes."""
        builder = PipelineGraphBuilder()
        builder.build()

        # Check nodes were added
        assert builder._graph is not None
        nodes = builder._graph.nodes
        assert "ingest" in nodes
        assert "enrich" in nodes
        assert "classify" in nodes
        assert "escalate" in nodes

    async def test_graph_routing_logic(self):
        """Test graph can be invoked with initial state."""
        graph = create_pipeline_graph(with_checkpointer=False)

        # Create state with no report (will fail gracefully)
        state = create_initial_state()

        config = {"configurable": {"thread_id": "test-routing"}}
        result = await graph.ainvoke(state, config)

        # Should complete with errors since no report
        assert "errors" in result
        assert len(result["errors"]) > 0


class TestValidatePath:
    """Tests for _validate_path helper."""

    def test_rejects_invalid_extension(self):
        """Test path with disallowed extension raises ValueError."""
        from siopv.application.orchestration.graph import _validate_path

        with pytest.raises(ValueError, match="Invalid file extension"):
            _validate_path(Path("/tmp/test.exe"), allowed_extensions={".db", ".sqlite"})

    def test_rejects_nonexistent_parent(self):
        """Test must_exist=True with missing parent raises ValueError."""
        from siopv.application.orchestration.graph import _validate_path

        with pytest.raises(ValueError, match="Parent directory does not exist"):
            _validate_path(
                Path("/nonexistent/deeply/nested/dir/file.db"),
                must_exist=True,
                allowed_extensions={".db"},
            )

    def test_accepts_valid_path(self):
        """Test valid path passes validation."""
        from siopv.application.orchestration.graph import _validate_path

        result = _validate_path(Path("/tmp/test.db"), allowed_extensions={".db"})
        assert result.name == "test.db"


class TestPipelineGraphBuilderErrors:
    """Tests for error branches in PipelineGraphBuilder."""

    def test_add_nodes_without_build_raises(self):
        """Test _add_nodes raises when graph not initialized."""
        builder = PipelineGraphBuilder()

        with pytest.raises(RuntimeError, match="Graph not initialized"):
            builder._add_nodes()

    def test_add_edges_without_build_raises(self):
        """Test _add_edges raises when graph not initialized."""
        builder = PipelineGraphBuilder()

        with pytest.raises(RuntimeError, match="Graph not initialized"):
            builder._add_edges()

    def test_compile_double_none_guard(self):
        """Test compile raises if build() somehow leaves graph as None."""
        from unittest.mock import patch

        builder = PipelineGraphBuilder()
        # Mock build() to be a no-op (doesn't set _graph), simulating silent failure
        with (
            patch.object(builder, "build", return_value=builder),
            pytest.raises(RuntimeError, match="Failed to build graph"),
        ):
            builder.compile(with_checkpointer=False)
