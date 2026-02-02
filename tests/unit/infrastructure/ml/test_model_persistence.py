"""Unit tests for ModelPersistence.

Tests model saving, loading, and metadata management.

FIXED: Uses tmp_path fixture properly and creates actual temp files for testing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from siopv.domain.exceptions import IntegrityError, PathTraversalError
from siopv.infrastructure.ml.model_persistence import (
    ModelPersistence,
    _compute_file_hash,
    _compute_hmac_signature,
    _validate_path_component,
)

# === Fixtures ===


@pytest.fixture
def temp_base_path(tmp_path: Path) -> Path:
    """Create a temporary directory for model storage using pytest tmp_path."""
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


@pytest.fixture
def model_persistence(temp_base_path: Path) -> ModelPersistence:
    """Create a ModelPersistence instance."""
    return ModelPersistence(base_path=temp_base_path)


@pytest.fixture
def model_persistence_with_signing(temp_base_path: Path) -> ModelPersistence:
    """Create a ModelPersistence instance with signing enabled."""
    return ModelPersistence(base_path=temp_base_path, signing_key="test-secret-key")


@pytest.fixture
def mock_model(tmp_path: Path) -> Mock:
    """Create a mock XGBoost model that actually writes files.

    FIXED: Creates actual files to test hash verification.
    """
    mock = Mock()

    def save_model_impl(path: str) -> None:
        """Actually write model data to file."""
        model_path = Path(path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        # Write realistic model JSON
        model_data = {
            "learner": {
                "attributes": {"best_iteration": "100", "best_score": "0.87"},
                "feature_names": ["f1", "f2"],
                "gradient_booster": {"model": {"trees": []}},
            }
        }
        model_path.write_text(json.dumps(model_data))

    mock.save_model = Mock(side_effect=save_model_impl)
    mock.load_model = Mock()
    return mock


# === Helper Function Tests ===


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_validate_path_component_valid(self):
        """Test validation of valid path components."""
        assert _validate_path_component("model_v1", "name") == "model_v1"
        assert _validate_path_component("1.0.0", "version") == "1.0.0"
        assert _validate_path_component("my-model.v2", "name") == "my-model.v2"

    def test_validate_path_component_empty(self):
        """Test validation rejects empty components."""
        with pytest.raises(PathTraversalError, match="Empty"):
            _validate_path_component("", "name")

    def test_validate_path_component_traversal(self):
        """Test validation rejects path traversal patterns."""
        with pytest.raises(PathTraversalError, match="traversal"):
            _validate_path_component("../etc/passwd", "name")

        with pytest.raises(PathTraversalError, match="traversal"):
            _validate_path_component("model/../../secret", "name")

    def test_validate_path_component_invalid_chars(self):
        """Test validation rejects invalid characters."""
        with pytest.raises(PathTraversalError, match="Invalid characters"):
            _validate_path_component("model name", "name")  # space

        with pytest.raises(PathTraversalError, match="Invalid characters"):
            _validate_path_component("model@v1", "name")  # @

    def test_compute_file_hash(self, tmp_path: Path):
        """Test file hash computation."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)

        # Compute expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()

        # Verify function produces same hash
        computed_hash = _compute_file_hash(test_file)
        assert computed_hash == expected_hash

    def test_compute_hmac_signature(self):
        """Test HMAC signature computation."""
        data = b"test data"
        key = "secret-key"

        signature = _compute_hmac_signature(data, key)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length


# === Initialization Tests ===


class TestModelPersistenceInit:
    """Tests for ModelPersistence initialization."""

    def test_init_creates_directory(self, tmp_path: Path):
        """Test that initialization creates base directory."""
        base_path = tmp_path / "new_models"
        assert not base_path.exists()

        ModelPersistence(base_path=base_path)

        assert base_path.exists()
        assert base_path.is_dir()

    def test_init_with_string_path(self, tmp_path: Path):
        """Test initialization with string path."""
        base_path = str(tmp_path / "models")

        persistence = ModelPersistence(base_path=base_path)

        assert persistence._base_path == Path(base_path).resolve()

    def test_init_with_existing_directory(self, temp_base_path: Path):
        """Test initialization with existing directory."""
        assert temp_base_path.exists()

        persistence = ModelPersistence(base_path=temp_base_path)

        assert persistence._base_path == temp_base_path.resolve()

    def test_init_with_signing_key(self, temp_base_path: Path):
        """Test initialization with signing key."""
        persistence = ModelPersistence(base_path=temp_base_path, signing_key="my-secret-key")

        assert persistence._signing_key == "my-secret-key"

    def test_init_with_custom_max_size(self, temp_base_path: Path):
        """Test initialization with custom max model size."""
        persistence = ModelPersistence(base_path=temp_base_path, max_model_size=50 * 1024 * 1024)

        assert persistence._max_model_size == 50 * 1024 * 1024


# === Save Model Tests ===


class TestModelPersistenceSave:
    """Tests for model saving functionality."""

    def test_save_model_with_metadata(
        self, model_persistence: ModelPersistence, mock_model: Mock, temp_base_path: Path
    ):
        """Test saving model with metadata."""
        model_path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="test_classifier",
            version="1.0.0",
            metrics={"f1": 0.87, "precision": 0.85},
            feature_names=["feature1", "feature2"],
        )

        # Verify model was saved
        assert model_path.exists()
        mock_model.save_model.assert_called_once()

        # Verify metadata was saved
        metadata_path = model_path.parent / "metadata.json"
        assert metadata_path.exists()

        with metadata_path.open() as f:
            metadata = json.load(f)

        assert metadata["model_name"] == "test_classifier"
        assert metadata["version"] == "1.0.0"
        assert metadata["metrics"]["f1"] == 0.87
        assert metadata["feature_names"] == ["feature1", "feature2"]
        assert "model_hash" in metadata
        assert metadata["hash_algorithm"] == "sha256"

    def test_save_model_creates_nested_directories(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test that save creates nested directories."""
        model_path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="nested_model",
            version="2.0.0",
        )

        assert model_path.exists()
        assert model_path.parent.name == "2.0.0"
        assert model_path.parent.parent.name == "nested_model"

    def test_save_model_with_minimal_metadata(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test saving with minimal metadata."""
        model_path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="minimal_model",
        )

        assert model_path.exists()

        # Check metadata has defaults
        metadata_path = model_path.parent / "metadata.json"
        with metadata_path.open() as f:
            metadata = json.load(f)

        assert metadata["version"] == "1.0.0"
        assert metadata["metrics"] == {}
        assert metadata["feature_names"] == []

    def test_save_model_with_extra_metadata(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test saving with extra metadata."""
        extra = {"author": "test", "description": "Test model"}

        model_path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="extra_model",
            extra_metadata=extra,
        )

        metadata_path = model_path.parent / "metadata.json"
        with metadata_path.open() as f:
            metadata = json.load(f)

        assert metadata["extra"]["author"] == "test"
        assert metadata["extra"]["description"] == "Test model"

    def test_save_model_includes_timestamp(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test that saved metadata includes timestamp."""
        model_path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="timestamped_model",
        )

        metadata_path = model_path.parent / "metadata.json"
        with metadata_path.open() as f:
            metadata = json.load(f)

        assert "created_at" in metadata
        # Should be ISO format timestamp
        assert "T" in metadata["created_at"]

    def test_save_model_with_signing(
        self, model_persistence_with_signing: ModelPersistence, mock_model: Mock
    ):
        """Test saving model with HMAC signature."""
        model_path = model_persistence_with_signing.save_model_with_metadata(
            model=mock_model,
            model_name="signed_model",
        )

        metadata_path = model_path.parent / "metadata.json"
        with metadata_path.open() as f:
            metadata = json.load(f)

        assert "model_signature" in metadata
        assert metadata["signature_algorithm"] == "hmac-sha256"

    def test_save_model_path_traversal_rejected(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test that path traversal in model_name is rejected."""
        with pytest.raises(PathTraversalError):
            model_persistence.save_model_with_metadata(
                model=mock_model,
                model_name="../../../etc/passwd",
            )

    def test_save_model_version_traversal_rejected(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test that path traversal in version is rejected."""
        with pytest.raises(PathTraversalError):
            model_persistence.save_model_with_metadata(
                model=mock_model,
                model_name="valid_model",
                version="../../../etc/passwd",
            )


# === Load Model Tests ===


class TestModelPersistenceLoad:
    """Tests for model loading functionality."""

    def test_load_model_with_metadata(self, model_persistence: ModelPersistence, mock_model: Mock):
        """Test loading model with metadata and integrity verification."""
        # First save a model
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="loadable_model",
            version="1.0.0",
            metrics={"f1": 0.90},
        )

        # Create a mock model class that returns a new mock
        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)

        # Load the model
        loaded_model, metadata = model_persistence.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="loadable_model",
            version="1.0.0",
        )

        assert loaded_model is loaded_mock
        assert metadata["version"] == "1.0.0"
        assert metadata["metrics"]["f1"] == 0.90
        loaded_mock.load_model.assert_called_once()

    def test_load_latest_version(self, model_persistence: ModelPersistence, mock_model: Mock):
        """Test loading latest version when version not specified."""
        # Save multiple versions
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="versioned_model",
            version="1.0.0",
        )
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="versioned_model",
            version="2.0.0",
        )

        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)

        # Load without specifying version
        loaded_model, metadata = model_persistence.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="versioned_model",
        )

        # Should load latest (2.0.0)
        assert metadata["version"] == "2.0.0"

    def test_load_nonexistent_model_raises_error(self, model_persistence: ModelPersistence):
        """Test loading non-existent model raises error."""
        mock_model_class = Mock()

        with pytest.raises(FileNotFoundError, match="Model not found"):
            model_persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="nonexistent",
            )

    def test_load_nonexistent_version_raises_error(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test loading non-existent version raises error."""
        # Save version 1.0.0
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="model",
            version="1.0.0",
        )

        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)

        # Try to load version 2.0.0
        with pytest.raises(FileNotFoundError):
            model_persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="model",
                version="2.0.0",
            )

    def test_load_model_integrity_check(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test that integrity verification works."""
        # Save a model
        model_path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="integrity_model",
            version="1.0.0",
        )

        # Tamper with the model file
        model_path.write_text('{"tampered": true}')

        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)

        # Loading should fail due to hash mismatch
        with pytest.raises(IntegrityError, match="hash mismatch"):
            model_persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="integrity_model",
                version="1.0.0",
            )

    def test_load_model_skip_integrity_check(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test loading with integrity check disabled."""
        # Save a model
        model_path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="skip_integrity_model",
            version="1.0.0",
        )

        # Tamper with the model file
        model_path.write_text('{"tampered": true}')

        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)

        # Loading should succeed when verify_integrity=False
        loaded_model, metadata = model_persistence.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="skip_integrity_model",
            version="1.0.0",
            verify_integrity=False,
        )

        assert loaded_model is loaded_mock

    def test_load_model_signature_verification(
        self, model_persistence_with_signing: ModelPersistence, mock_model: Mock
    ):
        """Test that signature verification works."""
        # Save a signed model
        model_persistence_with_signing.save_model_with_metadata(
            model=mock_model,
            model_name="signed_load_model",
            version="1.0.0",
        )

        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)

        # Loading should succeed with valid signature
        loaded_model, metadata = model_persistence_with_signing.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="signed_load_model",
            version="1.0.0",
        )

        assert loaded_model is loaded_mock

    def test_load_oversized_model_rejected(self, temp_base_path: Path, mock_model: Mock):
        """Test that oversized models are rejected."""
        # Create persistence with very small max size
        persistence = ModelPersistence(base_path=temp_base_path, max_model_size=10)

        # Save a model (will be larger than 10 bytes)
        persistence.save_model_with_metadata(
            model=mock_model,
            model_name="large_model",
            version="1.0.0",
        )

        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)

        # Loading should fail due to size
        with pytest.raises(IntegrityError, match="exceeds maximum"):
            persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="large_model",
                version="1.0.0",
            )

    def test_load_model_path_traversal_rejected(self, model_persistence: ModelPersistence):
        """Test that path traversal in model_name is rejected on load."""
        mock_model_class = Mock()

        with pytest.raises(PathTraversalError):
            model_persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="../../../etc/passwd",
            )


# === List Models Tests ===


class TestModelPersistenceList:
    """Tests for listing models functionality."""

    def test_list_models_empty(self, model_persistence: ModelPersistence):
        """Test listing when no models exist."""
        models = model_persistence.list_models()

        assert models == []

    def test_list_models_with_single_model(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test listing single model."""
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="single_model",
            version="1.0.0",
            metrics={"f1": 0.85},
        )

        models = model_persistence.list_models()

        assert len(models) == 1
        assert models[0]["name"] == "single_model"
        assert len(models[0]["versions"]) == 1
        assert models[0]["versions"][0]["version"] == "1.0.0"
        assert models[0]["versions"][0]["has_integrity_hash"] is True

    def test_list_models_with_multiple_versions(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test listing model with multiple versions."""
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="multi_version",
            version="1.0.0",
        )
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="multi_version",
            version="1.1.0",
        )
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="multi_version",
            version="2.0.0",
        )

        models = model_persistence.list_models()

        assert len(models) == 1
        assert len(models[0]["versions"]) == 3

    def test_list_models_with_multiple_models(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test listing multiple models."""
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="model_a",
            version="1.0.0",
        )
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="model_b",
            version="1.0.0",
        )

        models = model_persistence.list_models()

        assert len(models) == 2
        model_names = {m["name"] for m in models}
        assert model_names == {"model_a", "model_b"}


# === Get Latest Version Tests ===


class TestModelPersistenceGetLatest:
    """Tests for getting latest version."""

    def test_get_latest_version(self, model_persistence: ModelPersistence, mock_model: Mock):
        """Test getting latest version."""
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="versioned",
            version="1.0.0",
        )
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="versioned",
            version="2.0.0",
        )

        latest = model_persistence.get_latest_version("versioned")

        assert latest == "2.0.0"

    def test_get_latest_version_nonexistent(self, model_persistence: ModelPersistence):
        """Test getting latest version of non-existent model."""
        latest = model_persistence.get_latest_version("nonexistent")

        assert latest is None

    def test_get_latest_version_empty_model_dir(
        self, model_persistence: ModelPersistence, temp_base_path: Path
    ):
        """Test getting latest version when model dir is empty."""
        # Create empty model directory
        model_dir = temp_base_path / "empty_model"
        model_dir.mkdir()

        latest = model_persistence.get_latest_version("empty_model")

        assert latest is None

    def test_get_latest_version_path_traversal_rejected(self, model_persistence: ModelPersistence):
        """Test that path traversal is rejected."""
        with pytest.raises(PathTraversalError):
            model_persistence.get_latest_version("../etc/passwd")


# === Delete Model Tests ===


class TestModelPersistenceDelete:
    """Tests for deleting models."""

    def test_delete_specific_version(self, model_persistence: ModelPersistence, mock_model: Mock):
        """Test deleting a specific version."""
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="deletable",
            version="1.0.0",
        )
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="deletable",
            version="2.0.0",
        )

        result = model_persistence.delete_model("deletable", version="1.0.0")

        assert result is True
        # Version 1.0.0 should be gone
        assert model_persistence.get_latest_version("deletable") == "2.0.0"

    def test_delete_all_versions(self, model_persistence: ModelPersistence, mock_model: Mock):
        """Test deleting all versions of a model."""
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="deletable_all",
            version="1.0.0",
        )
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="deletable_all",
            version="2.0.0",
        )

        result = model_persistence.delete_model("deletable_all")

        assert result is True
        # Model should be completely gone
        assert model_persistence.get_latest_version("deletable_all") is None

    def test_delete_nonexistent_model_returns_false(self, model_persistence: ModelPersistence):
        """Test deleting non-existent model returns False."""
        result = model_persistence.delete_model("nonexistent")

        assert result is False

    def test_delete_nonexistent_version_returns_false(
        self, model_persistence: ModelPersistence, mock_model: Mock
    ):
        """Test deleting non-existent version returns False."""
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="model",
            version="1.0.0",
        )

        result = model_persistence.delete_model("model", version="2.0.0")

        assert result is False

    def test_delete_path_traversal_rejected(self, model_persistence: ModelPersistence):
        """Test that path traversal is rejected on delete."""
        with pytest.raises(PathTraversalError):
            model_persistence.delete_model("../etc/passwd")


# === Integration Tests ===


class TestModelPersistenceIntegration:
    """Integration tests for complete workflows."""

    def test_save_load_roundtrip(self, model_persistence: ModelPersistence, mock_model: Mock):
        """Test complete save and load cycle."""
        # Save model
        original_metrics = {"f1": 0.87, "precision": 0.85, "recall": 0.90}
        feature_names = ["f1", "f2", "f3"]

        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="roundtrip_model",
            version="1.0.0",
            metrics=original_metrics,
            feature_names=feature_names,
        )

        # Load model
        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)
        loaded_model, metadata = model_persistence.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="roundtrip_model",
            version="1.0.0",
        )

        # Verify
        assert loaded_model is loaded_mock
        assert metadata["metrics"] == original_metrics
        assert metadata["feature_names"] == feature_names

    def test_multiple_models_lifecycle(self, model_persistence: ModelPersistence, mock_model: Mock):
        """Test managing multiple models through their lifecycle."""
        # Create multiple models
        for i in range(3):
            model_persistence.save_model_with_metadata(
                model=mock_model,
                model_name=f"model_{i}",
                version="1.0.0",
            )

        # List all models
        models = model_persistence.list_models()
        assert len(models) == 3

        # Delete one model
        model_persistence.delete_model("model_1")

        # List again
        models = model_persistence.list_models()
        assert len(models) == 2

    def test_signed_model_workflow(
        self, model_persistence_with_signing: ModelPersistence, mock_model: Mock
    ):
        """Test complete workflow with signed models."""
        # Save signed model
        model_persistence_with_signing.save_model_with_metadata(
            model=mock_model,
            model_name="signed_workflow",
            version="1.0.0",
            metrics={"f1": 0.90},
        )

        # Load and verify signature
        loaded_mock = Mock()
        mock_model_class = Mock(return_value=loaded_mock)
        loaded_model, metadata = model_persistence_with_signing.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="signed_workflow",
            version="1.0.0",
        )

        assert loaded_model is loaded_mock
        assert "model_signature" in metadata
