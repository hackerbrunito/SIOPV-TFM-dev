"""Security unit tests for ModelPersistence.

Tests for:
- H-01: Path traversal protection
- M-01: Model integrity verification (SHA-256 hash, HMAC signature)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from siopv.domain.exceptions import IntegrityError, PathTraversalError
from siopv.infrastructure.ml.model_persistence import (
    DEFAULT_MAX_MODEL_SIZE,
    SAFE_PATH_COMPONENT_REGEX,
    ModelPersistence,
    _compute_file_hash,
    _compute_hmac_signature,
    _validate_path_component,
)

# === Fixtures ===


@pytest.fixture
def temp_base_path() -> Path:
    """Create a temporary directory for model storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def model_persistence(temp_base_path: Path) -> ModelPersistence:
    """Create a ModelPersistence instance without signing key."""
    return ModelPersistence(base_path=temp_base_path)


@pytest.fixture
def signed_model_persistence(temp_base_path: Path) -> ModelPersistence:
    """Create a ModelPersistence instance with signing key."""
    return ModelPersistence(
        base_path=temp_base_path,
        signing_key="test-signing-key-12345",
    )


@pytest.fixture
def mock_model():
    """Create a mock XGBoost model."""
    mock = Mock()

    def save_model_side_effect(path: str) -> None:
        """Write actual model content for hash testing."""
        with open(path, "w") as f:
            json.dump({"model": "test-xgboost-model", "version": "1.0"}, f)

    mock.save_model = Mock(side_effect=save_model_side_effect)
    mock.load_model = Mock()
    return mock


# === H-01: Path Traversal Protection Tests ===


class TestPathTraversalProtection:
    """Tests for H-01 path traversal protection."""

    @pytest.mark.parametrize(
        "model_name",
        [
            "../etc/passwd",
            "../../etc/passwd",
            "models/../../../etc/passwd",
            "..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
            "model\\name",
            "model/name",
        ],
        ids=[
            "single-parent-dir",
            "double-parent-dir",
            "nested-traversal",
            "windows-backslash-parent",
            "absolute-unix",
            "absolute-windows",
            "backslash-separator",
            "slash-separator",
        ],
    )
    def test_save_rejects_path_traversal(
        self,
        model_persistence: ModelPersistence,
        mock_model,
        model_name: str,
    ) -> None:
        """Test that save_model_with_metadata rejects path traversal attempts."""
        with pytest.raises(PathTraversalError, match="Path traversal"):
            model_persistence.save_model_with_metadata(
                model=mock_model,
                model_name=model_name,
            )

    @pytest.mark.parametrize(
        "model_name",
        [
            "../malicious",
            "..\\malicious",
            "/absolute/path",
            "contains/slash",
            "contains\\backslash",
        ],
    )
    def test_load_rejects_path_traversal(
        self, model_persistence: ModelPersistence, model_name: str
    ) -> None:
        """Test that load_model_with_metadata rejects path traversal."""
        mock_model_class = Mock()

        with pytest.raises(PathTraversalError, match="Path traversal"):
            model_persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name=model_name,
            )

    @pytest.mark.parametrize(
        "version",
        [
            "../escape",
            "../../etc",
            "1.0.0/../../etc",
            "v1\\..\\..\\etc",
        ],
    )
    def test_save_rejects_traversal_in_version(
        self, model_persistence: ModelPersistence, mock_model, version: str
    ) -> None:
        """Test that version parameter is also validated."""
        with pytest.raises(PathTraversalError, match="Path traversal"):
            model_persistence.save_model_with_metadata(
                model=mock_model,
                model_name="valid_model",
                version=version,
            )

    @pytest.mark.parametrize(
        "model_name",
        ["", "   "],
        ids=["empty", "whitespace"],
    )
    def test_rejects_empty_model_name(
        self, model_persistence: ModelPersistence, mock_model, model_name: str
    ) -> None:
        """Test that empty model names are rejected."""
        with pytest.raises(PathTraversalError, match="Empty"):
            model_persistence.save_model_with_metadata(
                model=mock_model,
                model_name=model_name.strip() if model_name.strip() else "",
            )

    @pytest.mark.parametrize(
        "invalid_char",
        [
            "model<name",
            "model>name",
            "model|name",
            "model:name",
            'model"name',
            "model*name",
            "model?name",
            "model name",
            "model\tname",
            "model\nname",
        ],
        ids=[
            "less-than",
            "greater-than",
            "pipe",
            "colon",
            "quote",
            "asterisk",
            "question-mark",
            "space",
            "tab",
            "newline",
        ],
    )
    def test_rejects_special_characters(
        self,
        model_persistence: ModelPersistence,
        mock_model,
        invalid_char: str,
    ) -> None:
        """Test that special characters are rejected."""
        with pytest.raises(PathTraversalError, match="Invalid characters"):
            model_persistence.save_model_with_metadata(
                model=mock_model,
                model_name=invalid_char,
            )

    @pytest.mark.parametrize(
        "valid_name",
        [
            "my_model",
            "my-model",
            "mymodel",
            "MyModel123",
            "model.v1",
            "model_v1.0.0",
            "classifier-2024-01-15",
            "xgboost_risk_v2.1.3",
        ],
        ids=[
            "underscore",
            "hyphen",
            "alphanumeric",
            "mixed-case",
            "with-dot",
            "version-dot",
            "date-format",
            "complex-valid",
        ],
    )
    def test_accepts_valid_model_names(
        self, model_persistence: ModelPersistence, mock_model, valid_name: str
    ) -> None:
        """Test that valid model names are accepted."""
        # Should not raise
        path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name=valid_name,
        )
        assert path.exists()

    def test_validate_resolved_path_prevents_escape(self, temp_base_path: Path) -> None:
        """Test that resolved path validation prevents directory escape."""
        persistence = ModelPersistence(base_path=temp_base_path)

        # Create a path that would escape base_path
        evil_path = temp_base_path / ".." / "etc" / "passwd"

        with pytest.raises(PathTraversalError, match="escapes base directory"):
            persistence._validate_resolved_path(evil_path)

    def test_delete_validates_model_name(self, model_persistence: ModelPersistence) -> None:
        """Test that delete_model validates model_name."""
        with pytest.raises(PathTraversalError, match="Path traversal"):
            model_persistence.delete_model("../malicious")

    def test_delete_validates_version(
        self, model_persistence: ModelPersistence, mock_model
    ) -> None:
        """Test that delete_model validates version."""
        # First save a valid model
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="valid_model",
            version="1.0.0",
        )

        with pytest.raises(PathTraversalError, match="Path traversal"):
            model_persistence.delete_model("valid_model", version="../escape")

    def test_get_latest_version_validates_name(self, model_persistence: ModelPersistence) -> None:
        """Test that get_latest_version validates model_name."""
        with pytest.raises(PathTraversalError, match="Path traversal"):
            model_persistence.get_latest_version("../malicious")


class TestValidatePathComponent:
    """Direct tests for _validate_path_component function."""

    @pytest.mark.parametrize(
        "component",
        ["valid", "valid_name", "valid-name", "valid.name", "Valid123"],
    )
    def test_valid_components(self, component: str) -> None:
        """Test that valid components pass through unchanged."""
        result = _validate_path_component(component, "test")
        assert result == component

    def test_raises_on_empty(self) -> None:
        """Test that empty component raises error."""
        with pytest.raises(PathTraversalError, match="Empty"):
            _validate_path_component("", "test_component")

    def test_raises_on_double_dot(self) -> None:
        """Test that .. raises error."""
        with pytest.raises(PathTraversalError, match="traversal attempt"):
            _validate_path_component("..", "test_component")

    def test_error_includes_component_name(self) -> None:
        """Test that error message includes component name."""
        with pytest.raises(PathTraversalError, match="model_name"):
            _validate_path_component("../bad", "model_name")


class TestSafePathRegex:
    """Tests for the SAFE_PATH_COMPONENT_REGEX."""

    @pytest.mark.parametrize(
        "valid",
        ["a", "ab", "a1", "a_b", "a-b", "a.b", "ABC123", "model_v1.0.0-beta"],
    )
    def test_matches_valid(self, valid: str) -> None:
        """Test regex matches valid patterns."""
        assert SAFE_PATH_COMPONENT_REGEX.match(valid)

    @pytest.mark.parametrize(
        "invalid",
        ["", " ", "/", "\\", "a/b", "a\\b", "a b", "a\tb"],
    )
    def test_rejects_invalid(self, invalid: str) -> None:
        """Test regex rejects invalid patterns.

        Note: '..' is actually matched by the regex (dots are allowed),
        but is rejected by the explicit check in _validate_path_component.
        """
        assert not SAFE_PATH_COMPONENT_REGEX.match(invalid)


# === M-01: Integrity Verification Tests ===


class TestIntegrityHashComputation:
    """Tests for SHA-256 hash computation (M-01)."""

    def test_compute_file_hash_deterministic(self, temp_base_path: Path) -> None:
        """Test that hash computation is deterministic."""
        # Create a test file
        test_file = temp_base_path / "test_model.json"
        content = b'{"model": "test", "weights": [1, 2, 3]}'
        test_file.write_bytes(content)

        # Compute hash twice
        hash1 = _compute_file_hash(test_file)
        hash2 = _compute_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length

    def test_hash_changes_when_file_changes(self, temp_base_path: Path) -> None:
        """Test that hash changes when file content changes."""
        test_file = temp_base_path / "test_model.json"

        # Original content
        test_file.write_bytes(b'{"version": 1}')
        hash1 = _compute_file_hash(test_file)

        # Modified content
        test_file.write_bytes(b'{"version": 2}')
        hash2 = _compute_file_hash(test_file)

        assert hash1 != hash2

    def test_hash_matches_python_hashlib(self, temp_base_path: Path) -> None:
        """Test that computed hash matches hashlib directly."""
        test_file = temp_base_path / "test_model.json"
        content = b'{"test": "content"}'
        test_file.write_bytes(content)

        computed_hash = _compute_file_hash(test_file)
        expected_hash = hashlib.sha256(content).hexdigest()

        assert computed_hash == expected_hash


class TestHMACSignature:
    """Tests for HMAC-SHA256 signature (M-01)."""

    def test_hmac_signature_generation(self) -> None:
        """Test HMAC signature is generated correctly."""
        data = b"model_hash_abc123"
        key = "secret-key-12345"

        signature = _compute_hmac_signature(data, key)

        # Verify format
        assert len(signature) == 64  # HMAC-SHA256 hex digest
        assert all(c in "0123456789abcdef" for c in signature)

    def test_hmac_verification_succeeds_with_correct_key(self) -> None:
        """Test HMAC verification succeeds with correct key."""
        data = b"model_hash_abc123"
        key = "secret-key-12345"

        signature = _compute_hmac_signature(data, key)

        # Verify by recomputing
        expected = hmac.new(key.encode(), data, hashlib.sha256).hexdigest()
        assert signature == expected

    def test_hmac_verification_fails_with_wrong_key(self) -> None:
        """Test HMAC verification fails with wrong key."""
        data = b"model_hash_abc123"
        correct_key = "correct-key"
        wrong_key = "wrong-key"

        signature = _compute_hmac_signature(data, correct_key)
        wrong_signature = _compute_hmac_signature(data, wrong_key)

        assert signature != wrong_signature

    def test_hmac_different_data_produces_different_signature(self) -> None:
        """Test that different data produces different signatures."""
        key = "same-key"
        data1 = b"hash1"
        data2 = b"hash2"

        sig1 = _compute_hmac_signature(data1, key)
        sig2 = _compute_hmac_signature(data2, key)

        assert sig1 != sig2


class TestModelIntegrityOnSave:
    """Tests for integrity hash stored on save (M-01)."""

    def test_save_includes_model_hash(
        self, model_persistence: ModelPersistence, mock_model
    ) -> None:
        """Test that saving model includes hash in metadata."""
        path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="test_model",
            version="1.0.0",
        )

        # Load metadata
        metadata_path = path.parent / "metadata.json"
        with metadata_path.open() as f:
            metadata = json.load(f)

        assert "model_hash" in metadata
        assert "hash_algorithm" in metadata
        assert metadata["hash_algorithm"] == "sha256"
        assert len(metadata["model_hash"]) == 64

    def test_save_includes_signature_when_key_configured(
        self, signed_model_persistence: ModelPersistence, mock_model
    ) -> None:
        """Test that saving with signing key includes signature."""
        path = signed_model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="signed_model",
            version="1.0.0",
        )

        metadata_path = path.parent / "metadata.json"
        with metadata_path.open() as f:
            metadata = json.load(f)

        assert "model_signature" in metadata
        assert "signature_algorithm" in metadata
        assert metadata["signature_algorithm"] == "hmac-sha256"

    def test_save_no_signature_without_key(
        self, model_persistence: ModelPersistence, mock_model
    ) -> None:
        """Test that saving without signing key does not include signature."""
        path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="unsigned_model",
            version="1.0.0",
        )

        metadata_path = path.parent / "metadata.json"
        with metadata_path.open() as f:
            metadata = json.load(f)

        assert "model_signature" not in metadata


class TestModelIntegrityOnLoad:
    """Tests for integrity verification on load (M-01)."""

    def test_load_verifies_hash(self, model_persistence: ModelPersistence, mock_model) -> None:
        """Test that load verifies model hash."""
        # Save model
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="verified_model",
            version="1.0.0",
        )

        # Create mock model class
        mock_model_class = Mock(return_value=mock_model)

        # Should load without error (hash matches)
        loaded_model, _metadata = model_persistence.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="verified_model",
            version="1.0.0",
            verify_integrity=True,
        )

        assert loaded_model is mock_model

    def test_load_fails_if_hash_mismatch(
        self, model_persistence: ModelPersistence, mock_model
    ) -> None:
        """Test that load fails if model hash doesn't match."""
        # Save model
        path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="tampered_model",
            version="1.0.0",
        )

        # Tamper with the model file
        with path.open("w") as f:
            json.dump({"tampered": "model"}, f)

        mock_model_class = Mock(return_value=mock_model)

        with pytest.raises(IntegrityError, match="hash mismatch"):
            model_persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="tampered_model",
                version="1.0.0",
                verify_integrity=True,
            )

    def test_load_verifies_signature_when_key_configured(
        self, temp_base_path: Path, mock_model
    ) -> None:
        """Test that load verifies HMAC signature when key is configured."""
        signing_key = "test-signing-key"
        persistence = ModelPersistence(
            base_path=temp_base_path,
            signing_key=signing_key,
        )

        # Save signed model
        persistence.save_model_with_metadata(
            model=mock_model,
            model_name="signed_model",
            version="1.0.0",
        )

        mock_model_class = Mock(return_value=mock_model)

        # Should load without error (signature matches)
        loaded_model, metadata = persistence.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="signed_model",
            version="1.0.0",
        )

        assert loaded_model is mock_model
        assert "model_signature" in metadata

    def test_load_fails_with_wrong_signing_key(self, temp_base_path: Path, mock_model) -> None:
        """Test that load fails when signing key doesn't match."""
        # Save with one key
        persistence1 = ModelPersistence(
            base_path=temp_base_path,
            signing_key="original-key",
        )
        persistence1.save_model_with_metadata(
            model=mock_model,
            model_name="key_mismatch",
            version="1.0.0",
        )

        # Try to load with different key
        persistence2 = ModelPersistence(
            base_path=temp_base_path,
            signing_key="different-key",
        )
        mock_model_class = Mock(return_value=mock_model)

        with pytest.raises(IntegrityError, match="signature verification failed"):
            persistence2.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="key_mismatch",
                version="1.0.0",
            )

    def test_load_skips_verification_when_disabled(
        self, model_persistence: ModelPersistence, mock_model
    ) -> None:
        """Test that verification can be disabled."""
        # Save model
        path = model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="skip_verify",
            version="1.0.0",
        )

        # Tamper with the model file
        with path.open("w") as f:
            json.dump({"tampered": "model"}, f)

        mock_model_class = Mock(return_value=mock_model)

        # Should NOT fail because verification is disabled
        loaded_model, _metadata = model_persistence.load_model_with_metadata(
            model_class=mock_model_class,
            model_name="skip_verify",
            version="1.0.0",
            verify_integrity=False,
        )

        assert loaded_model is mock_model


class TestFileSizeLimit:
    """Tests for file size limit enforcement (M-01)."""

    def test_load_fails_if_file_exceeds_size_limit(self, temp_base_path: Path) -> None:
        """Test that load fails if model file exceeds max size."""
        # Create persistence with very small limit
        small_limit = 100  # 100 bytes
        persistence = ModelPersistence(
            base_path=temp_base_path,
            max_model_size=small_limit,
        )

        # Manually create a model directory with large file
        model_dir = temp_base_path / "large_model" / "1.0.0"
        model_dir.mkdir(parents=True)

        model_path = model_dir / "model.json"
        # Write more than 100 bytes
        model_path.write_text("x" * 200)

        # Create metadata
        metadata_path = model_dir / "metadata.json"
        with metadata_path.open("w") as f:
            json.dump({"model_name": "large_model", "version": "1.0.0"}, f)

        mock_model_class = Mock()

        with pytest.raises(IntegrityError, match="exceeds maximum allowed size"):
            persistence.load_model_with_metadata(
                model_class=mock_model_class,
                model_name="large_model",
                version="1.0.0",
                verify_integrity=False,
            )

    def test_default_max_size_is_100mb(self, temp_base_path: Path) -> None:
        """Test that default max size is 100MB."""
        persistence = ModelPersistence(base_path=temp_base_path)
        assert persistence._max_model_size == DEFAULT_MAX_MODEL_SIZE
        assert DEFAULT_MAX_MODEL_SIZE == 100 * 1024 * 1024

    def test_custom_max_size_is_respected(self, temp_base_path: Path) -> None:
        """Test that custom max size is stored."""
        custom_size = 50 * 1024 * 1024  # 50MB
        persistence = ModelPersistence(
            base_path=temp_base_path,
            max_model_size=custom_size,
        )
        assert persistence._max_model_size == custom_size


class TestListModelsSkipsUnsafe:
    """Tests for list_models security behavior."""

    def test_list_models_skips_unsafe_directories(
        self, model_persistence: ModelPersistence, mock_model, temp_base_path: Path
    ) -> None:
        """Test that list_models skips directories with unsafe names."""
        # Save a valid model
        model_persistence.save_model_with_metadata(
            model=mock_model,
            model_name="valid_model",
            version="1.0.0",
        )

        # Manually create an unsafe directory (simulate attack)
        unsafe_dir = temp_base_path / "..unsafe"
        unsafe_dir.mkdir()
        (unsafe_dir / "1.0.0").mkdir()

        # List models
        models = model_persistence.list_models()

        # Should only include valid_model
        model_names = [m["name"] for m in models]
        assert "valid_model" in model_names
        assert "..unsafe" not in model_names
