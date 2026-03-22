"""SIOPV CLI - Command Line Interface.

Main entry point for the vulnerability orchestration system.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from siopv.infrastructure.config.settings import get_settings
from siopv.infrastructure.logging.setup import configure_logging, get_logger

if TYPE_CHECKING:
    import structlog

    from siopv.application.ports.jira_client import JiraClientPort
    from siopv.application.ports.metrics_exporter import MetricsExporterPort
    from siopv.application.ports.pdf_generator import PdfGeneratorPort
    from siopv.infrastructure.config.settings import Settings

app = typer.Typer(
    name="siopv",
    help="Sistema Inteligente de Orquestación y Priorización de Vulnerabilidades",
    no_args_is_help=True,
)

# Path to the Streamlit dashboard app (Phase 7)
STREAMLIT_APP_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
# Path to the Streamlit pipeline monitor (Phase B)
PIPELINE_MONITOR_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "pipeline_monitor.py"
# Path to the Streamlit analytics dashboard (Phase B — multi-page)
ANALYTICS_APP_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "analytics_app.py"


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
) -> None:
    """SIOPV - Intelligent Vulnerability Prioritization System."""
    settings = get_settings()
    configure_logging(
        level="DEBUG" if verbose or settings.debug else settings.log_level,
        json_format=not settings.debug and settings.environment == "production",
        app_name=settings.app_name,
    )


def _build_output_ports(
    settings: Settings,
    log: structlog.stdlib.BoundLogger,
) -> tuple[JiraClientPort | None, PdfGeneratorPort | None, MetricsExporterPort | None]:
    """Build Phase 8 output ports, gracefully degrading on failure.

    Returns:
        Tuple of (jira_port, pdf_port, metrics_port) — any may be None
    """
    from siopv.infrastructure.di import (  # noqa: PLC0415
        build_jira_adapter,
        build_metrics_exporter,
        build_pdf_adapter,
    )

    jira_port: JiraClientPort | None = None
    pdf_port: PdfGeneratorPort | None = None
    metrics_port: MetricsExporterPort | None = None
    try:
        jira_port = build_jira_adapter(settings)
    except Exception as exc:
        log.warning("jira_adapter_unavailable", error=str(exc))
    try:
        pdf_port = build_pdf_adapter(settings)
    except Exception as exc:
        log.warning("pdf_adapter_unavailable", error=str(exc))
    try:
        metrics_port = build_metrics_exporter(settings)
    except Exception as exc:
        log.warning("metrics_exporter_unavailable", error=str(exc))
    return jira_port, pdf_port, metrics_port


def _print_pipeline_summary(result: dict[str, object], output_dir: Path) -> None:
    """Print and save pipeline execution summary."""
    vuln_count = len(result.get("vulnerabilities", []))  # type: ignore[arg-type]
    classification_count = len(result.get("classifications", {}))  # type: ignore[arg-type]
    escalated_count = len(result.get("escalated_cves", []))  # type: ignore[arg-type]
    errors = result.get("errors", [])
    output_jira_keys = result.get("output_jira_keys", [])
    output_pdf_path = result.get("output_pdf_path")
    output_csv_path = result.get("output_csv_path")
    output_json_path = result.get("output_json_path")
    output_errors = result.get("output_errors", [])

    summary = {
        "report_path": str(result.get("report_path", "")),
        "vulnerabilities_ingested": vuln_count,
        "classifications": classification_count,
        "escalated_cves": escalated_count,
        "errors": errors,
        "authorization_allowed": result.get("authorization_allowed"),
        "output_jira_keys": output_jira_keys,
        "output_pdf_path": output_pdf_path,
        "output_csv_path": output_csv_path,
        "output_json_path": output_json_path,
        "output_errors": output_errors,
    }
    summary_path = output_dir / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    typer.echo(f"Vulnerabilities ingested: {vuln_count}")
    typer.echo(f"Classifications: {classification_count}")
    typer.echo(f"Escalated CVEs: {escalated_count}")
    if output_jira_keys:
        typer.echo(f"Jira tickets: {', '.join(output_jira_keys)}")  # type: ignore[arg-type]
    if output_pdf_path:
        typer.echo(f"PDF report: {output_pdf_path}")
    if output_json_path:
        typer.echo(f"JSON export: {output_json_path}")
    if output_csv_path:
        typer.echo(f"CSV export: {output_csv_path}")
    if errors:
        typer.echo(f"Errors: {len(errors)}", err=True)  # type: ignore[arg-type]
    if output_errors:
        typer.echo(f"Output errors: {len(output_errors)}", err=True)  # type: ignore[arg-type]
    typer.echo(f"Summary saved to: {summary_path}")


@app.command()
def process_report(
    report_path: Annotated[
        Path,
        typer.Argument(
            help="Path to Trivy JSON report",
            exists=True,
            readable=True,
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory for results"),
    ] = Path("./output"),
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", "-b", help="Batch size for processing"),
    ] = 50,
    user_id: Annotated[
        str | None,
        typer.Option("--user-id", "-u", help="User ID for authorization (Phase 5)"),
    ] = None,
    project_id: Annotated[
        str | None,
        typer.Option("--project-id", "-p", help="Project ID for authorization context"),
    ] = None,
) -> None:
    """Process a Trivy vulnerability report through the SIOPV pipeline."""
    from siopv.application.orchestration.graph import (  # noqa: PLC0415
        PipelinePorts,
        run_pipeline,
    )
    from siopv.infrastructure.di import (  # noqa: PLC0415
        build_classifier,
        build_epss_client,
        build_escalation_config,
        build_github_client,
        build_llm_analysis,
        build_nvd_client,
        build_osint_client,
        build_threshold_config,
        build_trivy_parser,
        build_vector_store,
        get_authorization_port,
        get_dual_layer_dlp_port,
    )

    log = get_logger(__name__)
    log.info(
        "processing_report",
        report_path=str(report_path),
        batch_size=batch_size,
        user_id=user_id,
        project_id=project_id,
    )

    typer.echo(f"Processing report: {report_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()

    # Resolve user_id and project_id: CLI flags override .env defaults
    resolved_user_id = user_id or settings.default_user_id
    resolved_project_id = project_id or settings.default_project_id

    jira_port, pdf_port, metrics_port = _build_output_ports(settings, log)

    ports = PipelinePorts(
        checkpoint_db_path=settings.checkpoint_db_path,
        trivy_parser=build_trivy_parser(),
        authorization_port=get_authorization_port(),
        dlp_port=get_dual_layer_dlp_port(),
        nvd_client=build_nvd_client(settings),
        epss_client=build_epss_client(settings),
        github_client=build_github_client(settings),
        osint_client=build_osint_client(settings),
        vector_store=build_vector_store(settings),
        classifier=build_classifier(settings),
        llm_analysis=build_llm_analysis(settings),
        jira=jira_port,
        pdf=pdf_port,
        metrics=metrics_port,
        threshold_config=build_threshold_config(settings),
        escalation_config=build_escalation_config(settings),
        batch_size=batch_size,
        output_dir=output_dir,
    )

    try:
        result = asyncio.run(
            run_pipeline(
                report_path=report_path,
                ports=ports,
                user_id=resolved_user_id,
                project_id=resolved_project_id,
            )
        )
    except Exception as exc:
        log.exception("pipeline_failed", error=str(exc))
        typer.echo(f"Pipeline failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    _print_pipeline_summary(dict(result), output_dir)


@app.command()
def dashboard() -> None:
    """Launch the Streamlit dashboard for Human-in-the-Loop review."""
    log = get_logger(__name__)
    log.info("launching_dashboard")

    if not STREAMLIT_APP_PATH.exists():
        typer.echo(
            f"Streamlit app not found at: {STREAMLIT_APP_PATH}\n"
            "The dashboard will be available after Phase 7 implementation.",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Launching Streamlit dashboard: {STREAMLIT_APP_PATH}")
    typer.echo("Dashboard will be available at http://localhost:8501")

    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(STREAMLIT_APP_PATH)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        log.exception("dashboard_launch_failed", error=str(exc))
        typer.echo(f"Failed to launch dashboard: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        typer.echo("\nDashboard stopped.")


@app.command()
def train_model(
    dataset_path: Annotated[
        Path,
        typer.Argument(
            help="Path to training dataset (CSV)",
            exists=True,
            readable=True,
        ),
    ],
    output_path: Annotated[
        Path,
        typer.Option("--output", "-o", help="Path to save trained model"),
    ] = Path("./models/xgboost_risk_model.json"),
    no_optimize: Annotated[
        bool,
        typer.Option("--no-optimize", help="Skip Optuna hyperparameter optimization"),
    ] = False,
    n_trials: Annotated[
        int,
        typer.Option("--n-trials", help="Number of Optuna trials"),
    ] = 50,
) -> None:
    """Train the XGBoost risk classification model."""
    import csv  # noqa: PLC0415

    from siopv.adapters.ml.xgboost_classifier import XGBoostClassifier  # noqa: PLC0415
    from siopv.domain.entities.ml_feature_vector import MLFeatureVector  # noqa: PLC0415

    log = get_logger(__name__)
    log.info("training_model", dataset_path=str(dataset_path))

    typer.echo(f"Loading dataset: {dataset_path}")

    # Load CSV with headers matching MLFeatureVector fields.
    # Required columns: cve_id + 14 feature columns + label (last column).
    # The last column must be the label (1=exploited, 0=not exploited).
    features: list[MLFeatureVector] = []
    labels: list[int] = []

    with dataset_path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            typer.echo("Dataset has no header row.", err=True)
            raise typer.Exit(code=1)

        label_column = reader.fieldnames[-1]

        for row in reader:
            if not row:
                continue
            label = int(row[label_column])
            feature_data = {k: v for k, v in row.items() if k != label_column}

            fv = MLFeatureVector(
                cve_id=str(feature_data.get("cve_id", f"UNKNOWN-{len(features)}")),
                cvss_base_score=float(feature_data["cvss_base_score"]),
                attack_vector=int(float(feature_data["attack_vector"])),
                attack_complexity=int(float(feature_data["attack_complexity"])),
                privileges_required=int(float(feature_data["privileges_required"])),
                user_interaction=int(float(feature_data["user_interaction"])),
                scope=int(float(feature_data["scope"])),
                confidentiality_impact=int(float(feature_data["confidentiality_impact"])),
                integrity_impact=int(float(feature_data["integrity_impact"])),
                availability_impact=int(float(feature_data["availability_impact"])),
                epss_score=float(feature_data["epss_score"]),
                epss_percentile=float(feature_data["epss_percentile"]),
                days_since_publication=int(float(feature_data["days_since_publication"])),
                has_exploit_ref=int(float(feature_data["has_exploit_ref"])),
                cwe_category=float(feature_data["cwe_category"]),
            )
            features.append(fv)
            labels.append(label)

    if not features:
        typer.echo("No training samples found in dataset.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Loaded {len(features)} samples ({sum(labels)} positive)")

    classifier = XGBoostClassifier()

    typer.echo("Training XGBoost classifier...")
    metrics = classifier.train(
        features,
        labels,
        optimize_hyperparams=not no_optimize,
        n_trials=n_trials,
    )

    typer.echo("Training complete. Metrics:")
    for key, value in metrics.items():
        typer.echo(f"  {key}: {value}")

    classifier.save_model(str(output_path))
    typer.echo(f"Model saved to: {output_path}")


@app.command()
def pipeline_monitor() -> None:
    """Launch the Streamlit Pipeline Monitor for real-time visualization."""
    log = get_logger(__name__)
    log.info("launching_pipeline_monitor")

    if not PIPELINE_MONITOR_PATH.exists():
        typer.echo(
            f"Pipeline monitor app not found at: {PIPELINE_MONITOR_PATH}",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Launching Pipeline Monitor: {PIPELINE_MONITOR_PATH}")
    typer.echo("Dashboard will be available at http://localhost:8501")

    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(PIPELINE_MONITOR_PATH)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        log.exception("pipeline_monitor_launch_failed", error=str(exc))
        typer.echo(f"Failed to launch pipeline monitor: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        typer.echo("\nPipeline monitor stopped.")


@app.command()
def analytics() -> None:
    """Launch the Security Analytics Dashboard (multi-page)."""
    log = get_logger(__name__)
    log.info("launching_analytics_dashboard")

    if not ANALYTICS_APP_PATH.exists():
        typer.echo(
            f"Analytics app not found at: {ANALYTICS_APP_PATH}",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Launching Security Analytics: {ANALYTICS_APP_PATH}")
    typer.echo("Dashboard will be available at http://localhost:8501")

    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(ANALYTICS_APP_PATH)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        log.exception("analytics_launch_failed", error=str(exc))
        typer.echo(f"Failed to launch analytics dashboard: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        typer.echo("\nAnalytics dashboard stopped.")


@app.command()
def version() -> None:
    """Show SIOPV version information."""
    typer.echo("SIOPV v0.1.0")
    typer.echo("Sistema Inteligente de Orquestación y Priorización de Vulnerabilidades")


if __name__ == "__main__":
    app()
