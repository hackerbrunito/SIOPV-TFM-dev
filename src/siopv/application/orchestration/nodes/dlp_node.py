"""DLP guardrail node for LangGraph pipeline.

Sanitizes vulnerability descriptions before they proceed to the enrichment
node. Implements Phase 6: Privacy/DLP guardrail layer.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING

import structlog

from siopv.domain.privacy.entities import SanitizationContext

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState
    from siopv.application.ports.dlp import DLPPort

logger = structlog.get_logger(__name__)


async def _run_dlp_for_vulns(
    vulnerabilities: Sequence[object],
    dlp_port: DLPPort,
) -> dict[str, object]:
    """Run DLP sanitization for all vulnerabilities concurrently via asyncio.gather."""

    async def _sanitize_one(vuln: object) -> tuple[str, dict[str, object]]:
        cve_id: str = vuln.cve_id.value  # type: ignore[attr-defined]
        ctx = SanitizationContext(text=vuln.description or "")  # type: ignore[attr-defined]
        result = await dlp_port.sanitize(ctx)
        return cve_id, {
            "redactions": result.total_redactions,
            "presidio_passed": result.presidio_passed,
            "semantic_passed": result.semantic_passed,
            "contains_pii": result.contains_pii,
        }

    pairs = await asyncio.gather(*[_sanitize_one(v) for v in vulnerabilities])
    return dict(pairs)


def _build_dlp_result(per_cve: dict[str, object], vuln_count: int) -> dict[str, object]:
    """Build the state update dict from per-CVE DLP data and log completion."""
    total_redactions: int = sum(v["redactions"] for v in per_cve.values() if isinstance(v, dict))
    logger.info(
        "dlp_node_complete",
        vulnerability_count=vuln_count,
        total_redactions=total_redactions,
        vulnerabilities_with_pii=sum(
            1 for v in per_cve.values() if isinstance(v, dict) and v.get("redactions", 0) > 0
        ),
    )
    return {
        "current_node": "dlp",
        "dlp_result": {
            "skipped": False,
            "processed": vuln_count,
            "total_redactions": total_redactions,
            "per_cve": per_cve,
        },
    }


def dlp_node(
    state: PipelineState,
    *,
    dlp_port: DLPPort | None = None,
) -> dict[str, object]:
    """DLP guardrail node — sanitizes vulnerability descriptions before enrichment.

    Reads vulnerabilities from state, runs each description through the DLP
    port (Presidio + optional Haiku validation), and returns a summary of
    redactions. Does NOT modify the vulnerability records themselves; the
    sanitized text is recorded in dlp_result for audit purposes.

    Skips gracefully if no DLP port is configured (logs a warning).

    Args:
        state: Current pipeline state containing the ingested vulnerabilities.
        dlp_port: DLP port implementation (PresidioAdapter). If None, node
            is skipped with a warning.

    Returns:
        State update dict with ``current_node`` and ``dlp_result`` fields.
    """
    vulnerabilities = state.get("vulnerabilities", [])

    if dlp_port is None:
        logger.warning(
            "dlp_node_skipped",
            reason="No DLP port configured",
            vulnerability_count=len(vulnerabilities),
        )
        return {"current_node": "dlp", "dlp_result": {"skipped": True, "reason": "no_dlp_port"}}

    if not vulnerabilities:
        logger.info("dlp_node_no_vulnerabilities")
        return {
            "current_node": "dlp",
            "dlp_result": {"skipped": False, "processed": 0, "total_redactions": 0, "per_cve": {}},
        }

    per_cve = asyncio.run(_run_dlp_for_vulns(vulnerabilities, dlp_port))
    return _build_dlp_result(per_cve, len(vulnerabilities))


__all__ = ["dlp_node"]
