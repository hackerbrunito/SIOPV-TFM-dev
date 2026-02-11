"""Model persistence utilities for ML models.

Handles saving and loading of trained models with metadata.

Security features:
- Path traversal protection (H-01)
- Model integrity verification via SHA-256 hash (M-01)
- Optional HMAC signature if MODEL_SIGNING_KEY is configured
- File size limits before loading
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from siopv.domain.exceptions import IntegrityError, PathTraversalError

logger = structlog.get_logger(__name__)

# Regex for safe path components: alphanumeric, dots, underscores, hyphens
SAFE_PATH_COMPONENT_REGEX = re.compile(r"^[a-zA-Z0-9._-]+$")

# Default max model file size: 100MB
DEFAULT_MAX_MODEL_SIZE = 100 * 1024 * 1024


def _validate_path_component(component: str, component_name: str = "path component") -> str:
    """Validate a path component against path traversal attacks.

    Args:
        component: The path component to validate (e.g., model_name, version)
        component_name: Human-readable name for error messages

    Returns:
        The validated component (unchanged if valid)

    Raises:
        PathTraversalError: If component contains unsafe characters
    """
    if not component:
        msg = f"Empty {component_name} not allowed"
        raise PathTraversalError(
            msg,
            details={"component_name": component_name},
        )

    # Check for path traversal patterns
    if ".." in component or "/" in component or "\\" in component:
        msg = f"Path traversal attempt detected in {component_name}"
        raise PathTraversalError(
            msg,
            details={"component_name": component_name, "value": component},
        )

    # Validate against whitelist regex
    if not SAFE_PATH_COMPONENT_REGEX.match(component):
        msg = (
            f"Invalid characters in {component_name}. "
            "Only alphanumeric, dots, underscores, and hyphens allowed."
        )
        raise PathTraversalError(
            msg,
            details={"component_name": component_name, "value": component},
        )

    return component


def _compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        path: Path to the file

    Returns:
        Hex-encoded SHA-256 hash
    """
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _compute_hmac_signature(data: bytes, key: str) -> str:
    """Compute HMAC-SHA256 signature.

    Args:
        data: Data to sign
        key: Secret key for HMAC

    Returns:
        Hex-encoded HMAC signature
    """
    return hmac.new(key.encode(), data, hashlib.sha256).hexdigest()


class ModelPersistence:
    """Utility class for model persistence operations.

    Handles saving/loading XGBoost models with associated metadata.
    Includes security features for path traversal protection and integrity verification.
    """

    def __init__(
        self,
        base_path: str | Path,
        *,
        signing_key: str | None = None,
        max_model_size: int = DEFAULT_MAX_MODEL_SIZE,
    ) -> None:
        """Initialize model persistence.

        Args:
            base_path: Base directory for model storage
            signing_key: Optional HMAC key for model signing (from MODEL_SIGNING_KEY env)
            max_model_size: Maximum allowed model file size in bytes (default 100MB)
        """
        self._base_path = Path(base_path).resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._signing_key = signing_key
        self._max_model_size = max_model_size

        logger.info(
            "model_persistence_initialized",
            base_path=str(self._base_path),
            signing_enabled=signing_key is not None,
            max_model_size_mb=max_model_size / (1024 * 1024),
        )

    def _validate_resolved_path(self, path: Path) -> None:
        """Verify that resolved path is within base_path.

        Args:
            path: Path to validate

        Raises:
            PathTraversalError: If path escapes base_path
        """
        resolved = path.resolve()
        if not resolved.is_relative_to(self._base_path):
            msg = "Path traversal attempt: resolved path escapes base directory"
            raise PathTraversalError(
                msg,
                details={
                    "resolved_path": str(resolved),
                    "base_path": str(self._base_path),
                },
            )

    def save_model_with_metadata(
        self,
        model: object,
        model_name: str,
        *,
        version: str = "1.0.0",
        metrics: dict[str, float] | None = None,
        feature_names: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save model with associated metadata and integrity hash.

        Args:
            model: XGBoost model with save_model method
            model_name: Name for the model (validated for path safety)
            version: Version string (validated for path safety)
            metrics: Training/evaluation metrics
            feature_names: List of feature names
            extra_metadata: Additional metadata to store

        Returns:
            Path to saved model

        Raises:
            PathTraversalError: If model_name or version contains unsafe characters
        """
        # Validate path components (H-01 fix)
        _validate_path_component(model_name, "model_name")
        _validate_path_component(version, "version")

        # Create versioned directory
        model_dir = self._base_path / model_name / version
        self._validate_resolved_path(model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = model_dir / "model.json"
        # model typed as object; xgboost.Booster.save_model exists at runtime
        model.save_model(str(model_path))  # type: ignore[attr-defined]

        # Compute model hash (M-01 fix)
        model_hash = _compute_file_hash(model_path)

        # Build metadata with integrity hash
        metadata: dict[str, Any] = {
            "model_name": model_name,
            "version": version,
            "created_at": datetime.now(UTC).isoformat(),
            "feature_names": feature_names or [],
            "metrics": metrics or {},
            "extra": extra_metadata or {},
            "model_hash": model_hash,
            "hash_algorithm": "sha256",
        }

        # Add HMAC signature if signing key is configured
        if self._signing_key:
            # Sign the model hash
            signature = _compute_hmac_signature(model_hash.encode(), self._signing_key)
            metadata["model_signature"] = signature
            metadata["signature_algorithm"] = "hmac-sha256"

        # Save metadata
        metadata_path = model_dir / "metadata.json"
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            "model_saved_with_metadata",
            model_path=str(model_path),
            version=version,
            model_hash=model_hash[:16] + "...",
            signed=self._signing_key is not None,
        )

        return model_path

    def _get_version_directory(self, model_dir: Path, version: str | None) -> Path:
        """Get version directory, either specific version or latest."""
        if version:
            _validate_path_component(version, "version")
            return model_dir / version

        # Get latest version (only consider valid directory names)
        valid_versions = [
            d for d in model_dir.iterdir() if d.is_dir() and SAFE_PATH_COMPONENT_REGEX.match(d.name)
        ]
        if not valid_versions:
            msg = f"No versions found for model: {model_dir.name}"
            raise FileNotFoundError(msg)
        return sorted(valid_versions)[-1]

    def _verify_model_integrity(self, model_path: Path, metadata: dict[str, Any]) -> None:
        """Verify model integrity using hash and optional signature."""
        stored_hash = metadata["model_hash"]
        computed_hash = _compute_file_hash(model_path)

        if computed_hash != stored_hash:
            msg = "Model integrity verification failed: hash mismatch"
            raise IntegrityError(
                msg,
                details={
                    "stored_hash": stored_hash[:16] + "...",
                    "computed_hash": computed_hash[:16] + "...",
                    "model_path": str(model_path),
                },
            )

        # Verify HMAC signature if signing key is available
        if self._signing_key and "model_signature" in metadata:
            expected_signature = _compute_hmac_signature(stored_hash.encode(), self._signing_key)
            if metadata["model_signature"] != expected_signature:
                msg = "Model signature verification failed"
                raise IntegrityError(
                    msg,
                    details={"model_path": str(model_path)},
                )

        logger.debug(
            "model_integrity_verified",
            model_path=str(model_path),
            hash_verified=True,
            signature_verified=self._signing_key is not None,
        )

    def load_model_with_metadata(
        self,
        model_class: type[Any],
        model_name: str,
        version: str | None = None,
        *,
        verify_integrity: bool = True,
    ) -> tuple[Any, dict[str, Any]]:
        """Load model with associated metadata and verify integrity.

        Args:
            model_class: Class to instantiate (e.g., XGBClassifier)
            model_name: Name of the model (validated for path safety)
            version: Specific version or None for latest (validated for path safety)
            verify_integrity: Whether to verify model hash (default True)

        Returns:
            Tuple of (model, metadata)

        Raises:
            PathTraversalError: If model_name or version contains unsafe characters
            IntegrityError: If model hash verification fails
            FileNotFoundError: If model not found
        """
        # Validate model_name (H-01 fix)
        _validate_path_component(model_name, "model_name")

        model_dir = self._base_path / model_name
        self._validate_resolved_path(model_dir)

        if not model_dir.exists():
            msg = f"Model not found: {model_name}"
            raise FileNotFoundError(msg)

        # Get version directory
        version_dir = self._get_version_directory(model_dir, version)
        self._validate_resolved_path(version_dir)

        # Load model
        model_path = version_dir / "model.json"
        if not model_path.exists():
            msg = f"Model file not found: {model_path}"
            raise FileNotFoundError(msg)

        # Check file size before loading (M-01 fix)
        file_size = model_path.stat().st_size
        if file_size > self._max_model_size:
            msg = f"Model file exceeds maximum allowed size ({self._max_model_size} bytes)"
            raise IntegrityError(
                msg,
                details={
                    "file_size": file_size,
                    "max_size": self._max_model_size,
                    "model_path": str(model_path),
                },
            )

        # Load metadata
        metadata_path = version_dir / "metadata.json"
        metadata: dict[str, Any] = {}
        if metadata_path.exists():
            with metadata_path.open() as f:
                metadata = json.load(f)

        # Verify integrity before loading (M-01 fix)
        if verify_integrity and "model_hash" in metadata:
            self._verify_model_integrity(model_path, metadata)

        # Now safe to load the model
        model = model_class()
        model.load_model(str(model_path))

        logger.info(
            "model_loaded_with_metadata",
            model_path=str(model_path),
            version=metadata.get("version", "unknown"),
            integrity_verified=verify_integrity,
        )

        return model, metadata

    def list_models(self) -> list[dict[str, Any]]:
        """List all available models with their versions.

        Only lists models with valid (safe) names.

        Returns:
            List of model info dictionaries
        """
        models = []

        for model_dir in self._base_path.iterdir():
            if not model_dir.is_dir():
                continue

            # Skip directories with unsafe names (H-01 protection)
            if not SAFE_PATH_COMPONENT_REGEX.match(model_dir.name):
                logger.warning(
                    "skipping_unsafe_model_directory",
                    directory=model_dir.name,
                )
                continue

            model_info: dict[str, Any] = {
                "name": model_dir.name,
                "versions": [],
            }

            for version_dir in sorted(model_dir.iterdir()):
                if not version_dir.is_dir():
                    continue

                # Skip versions with unsafe names
                if not SAFE_PATH_COMPONENT_REGEX.match(version_dir.name):
                    continue

                metadata_path = version_dir / "metadata.json"
                if metadata_path.exists():
                    with metadata_path.open() as f:
                        metadata = json.load(f)
                    model_info["versions"].append(
                        {
                            "version": version_dir.name,
                            "created_at": metadata.get("created_at"),
                            "metrics": metadata.get("metrics", {}),
                            "has_integrity_hash": "model_hash" in metadata,
                            "has_signature": "model_signature" in metadata,
                        }
                    )

            if model_info["versions"]:
                models.append(model_info)

        return models

    def get_latest_version(self, model_name: str) -> str | None:
        """Get the latest version of a model.

        Args:
            model_name: Name of the model (validated for path safety)

        Returns:
            Latest version string or None if not found

        Raises:
            PathTraversalError: If model_name contains unsafe characters
        """
        # Validate model_name (H-01 fix)
        _validate_path_component(model_name, "model_name")

        model_dir = self._base_path / model_name
        self._validate_resolved_path(model_dir)

        if not model_dir.exists():
            return None

        # Only consider valid version directories
        valid_versions = []
        for d in model_dir.iterdir():
            if d.is_dir() and SAFE_PATH_COMPONENT_REGEX.match(d.name):
                valid_versions.append(d)

        if not valid_versions:
            return None

        return sorted(valid_versions)[-1].name

    def delete_model(self, model_name: str, version: str | None = None) -> bool:
        """Delete a model version or all versions.

        Args:
            model_name: Name of the model (validated for path safety)
            version: Specific version or None to delete all (validated for path safety)

        Returns:
            True if deleted, False if not found

        Raises:
            PathTraversalError: If model_name or version contains unsafe characters
        """
        # Validate path components (H-01 fix)
        _validate_path_component(model_name, "model_name")

        model_dir = self._base_path / model_name
        self._validate_resolved_path(model_dir)

        if not model_dir.exists():
            return False

        if version:
            _validate_path_component(version, "version")
            version_dir = model_dir / version
            self._validate_resolved_path(version_dir)

            if version_dir.exists():
                shutil.rmtree(version_dir)
                logger.info("model_version_deleted", model=model_name, version=version)
                return True
            return False

        shutil.rmtree(model_dir)
        logger.info("model_deleted", model=model_name)
        return True


__all__ = ["ModelPersistence"]
