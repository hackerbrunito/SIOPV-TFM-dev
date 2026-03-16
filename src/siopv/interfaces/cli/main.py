"""SIOPV CLI - Command Line Interface.

Main entry point for the vulnerability orchestration system.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from siopv.infrastructure.config.settings import get_settings
from siopv.infrastructure.logging.setup import configure_logging, get_logger

app = typer.Typer(
    name="siopv",
    help="Sistema Inteligente de Orquestación y Priorización de Vulnerabilidades",
    no_args_is_help=True,
)

# Path to the Streamlit dashboard app (Phase 7)
# TODO(phase-7): Update this path once the Streamlit app is created
STREAMLIT_APP_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"


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
        level="DEBUG" if verbose else settings.log_level,
        json_format=settings.environment == "production",
    )


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
    from siopv.application.orchestration.graph import run_pipeline  # noqa: PLC0415
    from siopv.infrastructure.di import (  # noqa: PLC0415
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

    authorization_port = get_authorization_port()
    dlp_port = get_dual_layer_dlp_port()

    try:
        result = asyncio.run(
            run_pipeline(
                report_path=report_path,
                user_id=user_id,
                project_id=project_id,
                authorization_port=authorization_port,
                dlp_port=dlp_port,
                # TODO(phase-7): Wire enrichment clients and classifier via DI
            )
        )
    except Exception as exc:
        log.exception("pipeline_failed", error=str(exc))
        typer.echo(f"Pipeline failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Write summary to output directory
    vuln_count = len(result.get("vulnerabilities", []))
    classification_count = len(result.get("classifications", {}))
    escalated_count = len(result.get("escalated_cves", []))
    errors = result.get("errors", [])

    summary = {
        "report_path": str(report_path),
        "vulnerabilities_ingested": vuln_count,
        "classifications": classification_count,
        "escalated_cves": escalated_count,
        "errors": errors,
        "authorization_allowed": result.get("authorization_allowed"),
    }
    summary_path = output_dir / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    typer.echo(f"Vulnerabilities ingested: {vuln_count}")
    typer.echo(f"Classifications: {classification_count}")
    typer.echo(f"Escalated CVEs: {escalated_count}")
    if errors:
        typer.echo(f"Errors: {len(errors)}", err=True)
    typer.echo(f"Summary saved to: {summary_path}")


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
def version() -> None:
    """Show SIOPV version information."""
    typer.echo("SIOPV v0.1.0")
    typer.echo("Sistema Inteligente de Orquestación y Priorización de Vulnerabilidades")


if __name__ == "__main__":
    app()
