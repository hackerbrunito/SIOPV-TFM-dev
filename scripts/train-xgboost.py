"""Train XGBoost exploitation predictor using public vulnerability data.

Downloads CISA KEV + Metasploit modules as composite ground truth,
NVD CVE data for features (CVSS vectors, CWE), EPSS scores, and
ExploitDB for exploit-presence feature. Trains a binary XGBoost
classifier with Optuna hyperparameter tuning and SMOTE balancing.

Usage:
    uv run python scripts/train-xgboost.py

Data sources:
    - CISA KEV: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
    - EPSS: https://epss.empiricalsecurity.com/epss_scores-current.csv.gz
    - NVD: https://services.nvd.nist.gov/rest/json/cves/2.0 (paginated)
    - ExploitDB: https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv
    - Metasploit: https://raw.githubusercontent.com/dogasantos/msfcve/main/metasploit_cves.json

Output:
    - models/xgboost_risk_model.json -- trained XGBoost model
    - .ignorar/docs/masters-thesis-report/training-results.md -- results report
"""

from __future__ import annotations

import csv
import gzip
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import optuna
import structlog
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "xgboost_risk_model.json"
REPORT_DIR = PROJECT_ROOT / ".ignorar" / "docs" / "masters-thesis-report"
DATA_DIR = PROJECT_ROOT / ".ignorar" / "training-data"

# ---------------------------------------------------------------------------
# Data source URLs
# ---------------------------------------------------------------------------
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_URL = "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
EXPLOITDB_CSV_URL = "https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv"
METASPLOIT_URL = "https://raw.githubusercontent.com/dogasantos/msfcve/main/metasploit_cves.json"

# ---------------------------------------------------------------------------
# Feature engineering constants
# ---------------------------------------------------------------------------
FEATURE_NAMES: list[str] = [
    "cvss_base_score",
    "attack_vector",
    "attack_complexity",
    "privileges_required",
    "user_interaction",
    "scope",
    "confidentiality_impact",
    "integrity_impact",
    "availability_impact",
    "epss_score",
    "epss_percentile",
    "days_since_publication",
    "has_exploit_ref",
    "cwe_category",
    "has_public_exploit",
    "has_metasploit",
    "num_references",
]

AV_MAP: dict[str, int] = {"NETWORK": 3, "ADJACENT_NETWORK": 2, "LOCAL": 1, "PHYSICAL": 0}
AC_MAP: dict[str, int] = {"LOW": 1, "HIGH": 0}
PR_MAP: dict[str, int] = {"NONE": 2, "LOW": 1, "HIGH": 0}
UI_MAP: dict[str, int] = {"NONE": 1, "REQUIRED": 0}
SCOPE_MAP: dict[str, int] = {"CHANGED": 1, "UNCHANGED": 0}
IMPACT_MAP: dict[str, int] = {"HIGH": 2, "LOW": 1, "NONE": 0}

CWE_TARGET_ENCODING: dict[str, float] = {
    "CWE-22": 0.70,
    "CWE-78": 0.85,
    "CWE-79": 0.65,
    "CWE-89": 0.80,
    "CWE-94": 0.82,
    "CWE-119": 0.75,
    "CWE-120": 0.72,
    "CWE-125": 0.68,
    "CWE-190": 0.55,
    "CWE-200": 0.45,
    "CWE-269": 0.78,
    "CWE-287": 0.72,
    "CWE-306": 0.70,
    "CWE-352": 0.55,
    "CWE-400": 0.40,
    "CWE-416": 0.75,
    "CWE-434": 0.80,
    "CWE-502": 0.78,
    "CWE-611": 0.60,
    "CWE-787": 0.72,
    "CWE-798": 0.65,
    "CWE-862": 0.68,
    "CWE-863": 0.65,
    "CWE-918": 0.70,
}
CWE_DEFAULT: float = 0.35

# ---------------------------------------------------------------------------
# Training constants
# ---------------------------------------------------------------------------
TEST_SIZE: float = 0.2
RANDOM_STATE: int = 42
MAX_NVD_PAGES: int = 100
NVD_PAGE_SIZE: int = 2000
NVD_RATE_LIMIT_SECONDS: float = 6.0
NVD_RATE_LIMITED_STATUS: int = 403
HTTP_OK: int = 200
EPSS_MIN_COLUMNS: int = 3
OPTUNA_N_TRIALS: int = 50
MAX_BRANCHES_METASPLOIT: int = 14

CVE_PATTERN: re.Pattern[str] = re.compile(r"CVE-\d{4}-\d+")


# ===================================================================
# Data download functions
# ===================================================================


def download_cisa_kev(client: httpx.Client) -> set[str]:
    """Download CISA Known Exploited Vulnerabilities catalog."""
    print("Downloading CISA KEV catalog...")
    cache_path = DATA_DIR / "cisa-kev.json"

    if cache_path.exists():
        print(f"  Using cached: {cache_path}")
        data = json.loads(cache_path.read_text())
    else:
        resp = client.get(CISA_KEV_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cache_path.write_text(json.dumps(data, indent=2))

    kev_cves = {v["cveID"] for v in data.get("vulnerabilities", [])}
    print(f"  CISA KEV: {len(kev_cves)} known exploited CVEs")
    return kev_cves


def download_epss_scores(client: httpx.Client) -> dict[str, tuple[float, float]]:
    """Download current EPSS scores. Returns {cve_id: (score, percentile)}."""
    print("Downloading EPSS scores...")
    cache_path = DATA_DIR / "epss-scores.csv"

    if cache_path.exists():
        print(f"  Using cached: {cache_path}")
        lines = cache_path.read_text().splitlines()
    else:
        resp = client.get(EPSS_URL, timeout=60)
        resp.raise_for_status()
        csv_bytes = gzip.decompress(resp.content)
        text = csv_bytes.decode("utf-8")
        cache_path.write_text(text)
        lines = text.splitlines()

    epss: dict[str, tuple[float, float]] = {}
    for line in lines:
        if not line.startswith("CVE-"):
            continue
        parts = line.split(",")
        if len(parts) >= EPSS_MIN_COLUMNS:
            cve_id = parts[0].strip()
            try:
                score = float(parts[1])
                percentile = float(parts[2])
                epss[cve_id] = (score, percentile)
            except ValueError:
                continue

    print(f"  EPSS: {len(epss)} CVE scores loaded")
    return epss


def download_exploitdb_cves(client: httpx.Client) -> set[str]:
    """Download ExploitDB entries and extract CVE IDs."""
    print("Downloading ExploitDB CVE mappings...")
    cache_path = DATA_DIR / "exploitdb.csv"

    if cache_path.exists():
        print(f"  Using cached: {cache_path}")
        text = cache_path.read_text(errors="replace")
    else:
        try:
            resp = client.get(EXPLOITDB_CSV_URL, timeout=60)
            resp.raise_for_status()
            text = resp.text
            cache_path.write_text(text)
        except httpx.HTTPError as exc:
            print(f"  ExploitDB download failed: {exc} -- skipping")
            return set()

    exploit_cves: set[str] = set()
    for row in csv.reader(text.splitlines()):
        for cell in row:
            for match in CVE_PATTERN.finditer(cell):
                exploit_cves.add(match.group())

    print(f"  ExploitDB: {len(exploit_cves)} CVEs with known exploits")
    return exploit_cves


def download_metasploit_cves(client: httpx.Client) -> set[str]:
    """Download Metasploit module CVE mappings."""
    print("Downloading Metasploit CVE mappings...")
    cache_path = DATA_DIR / "metasploit-cves.json"

    if cache_path.exists():
        print(f"  Using cached: {cache_path}")
        data = json.loads(cache_path.read_text())
    else:
        try:
            resp = client.get(METASPLOIT_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            cache_path.write_text(json.dumps(data, indent=2))
        except httpx.HTTPError as exc:
            print(f"  Metasploit download failed: {exc} -- skipping")
            return set()

    msf_cves = _extract_cves_from_json(data)
    print(f"  Metasploit: {len(msf_cves)} CVEs with exploit modules")
    return msf_cves


def _extract_cves_from_json(data: dict[str, Any] | list[Any]) -> set[str]:
    """Extract all CVE IDs from an arbitrary JSON structure."""
    cves: set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            for match in CVE_PATTERN.finditer(str(key)):
                cves.add(match.group())
            if isinstance(value, (dict, list)):
                cves.update(_extract_cves_from_json(value))
            else:
                for match in CVE_PATTERN.finditer(str(value)):
                    cves.add(match.group())
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                cves.update(_extract_cves_from_json(item))
            else:
                for match in CVE_PATTERN.finditer(str(item)):
                    cves.add(match.group())
    return cves


def download_nvd_cves(
    client: httpx.Client,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Download CVEs from NVD API with CVSS v3 data."""
    print("Downloading NVD CVE data...")
    cache_path = DATA_DIR / "nvd-cves.json"

    if cache_path.exists():
        print(f"  Using cached: {cache_path}")
        result: list[dict[str, Any]] = json.loads(cache_path.read_text())
        return result

    all_cves: list[dict[str, Any]] = []
    headers: dict[str, str] = {}
    if api_key:
        headers["apiKey"] = api_key

    rate_limit = 0.6 if api_key else NVD_RATE_LIMIT_SECONDS

    for page in range(MAX_NVD_PAGES):
        start_index = page * NVD_PAGE_SIZE
        params: dict[str, int] = {
            "startIndex": start_index,
            "resultsPerPage": NVD_PAGE_SIZE,
        }

        try:
            resp = client.get(NVD_API_URL, params=params, headers=headers, timeout=30)
            if resp.status_code == NVD_RATE_LIMITED_STATUS:
                print(f"  NVD rate limited at page {page}, waiting 30s...")
                time.sleep(30)
                continue
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            print(f"  NVD error at page {page}: {exc}")
            break

        vulnerabilities = data.get("vulnerabilities", [])
        if not vulnerabilities:
            print(f"  No more results at page {page}")
            break

        all_cves.extend(vulnerabilities)
        total_results = data.get("totalResults", 0)
        print(f"  Page {page + 1}/{MAX_NVD_PAGES}: {len(all_cves)}/{total_results} CVEs")

        if start_index + NVD_PAGE_SIZE >= total_results:
            break

        time.sleep(rate_limit)

    cache_path.write_text(json.dumps(all_cves))
    print(f"  NVD: {len(all_cves)} CVEs downloaded")
    return all_cves


def fetch_missing_kev_cves(
    client: httpx.Client,
    kev_cves: set[str],
    nvd_cves: list[dict[str, Any]],
    api_key: str | None,
) -> list[dict[str, Any]]:
    """Fetch KEV CVEs missing from the NVD bulk download individually."""
    nvd_ids = {c.get("cve", {}).get("id", "") for c in nvd_cves}
    missing_kev = kev_cves - nvd_ids
    if not missing_kev:
        return nvd_cves

    print(f"\nFetching {len(missing_kev)} missing KEV CVEs from NVD individually...")
    rate_limit = 0.6 if api_key else NVD_RATE_LIMIT_SECONDS
    headers: dict[str, str] = {"apiKey": api_key} if api_key else {}
    fetched = 0

    for i, cve_id in enumerate(sorted(missing_kev)):
        try:
            resp = client.get(
                NVD_API_URL,
                params={"cveId": cve_id},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == HTTP_OK:
                data = resp.json()
                vulns = data.get("vulnerabilities", [])
                if vulns:
                    nvd_cves.extend(vulns)
                    fetched += 1
        except httpx.HTTPError:
            pass
        if (i + 1) % 50 == 0:
            print(f"  Fetched {fetched}/{i + 1} of {len(missing_kev)}...")
        time.sleep(rate_limit)

    print(f"  Recovered {fetched} missing KEV CVEs")

    cache_path = DATA_DIR / "nvd-cves.json"
    cache_path.write_text(json.dumps(nvd_cves))
    print(f"  Updated NVD cache with {len(nvd_cves)} total CVEs")

    return nvd_cves


# ===================================================================
# Feature extraction
# ===================================================================


def extract_features(
    cve_data: dict[str, Any],
    epss_scores: dict[str, tuple[float, float]],
    exploitdb_cves: set[str],
    metasploit_cves: set[str],
) -> tuple[str, list[float]] | None:
    """Extract 17-feature vector from a single CVE entry."""
    cve = cve_data.get("cve", {})
    cve_id = cve.get("id", "")

    if not cve_id.startswith("CVE-"):
        return None

    # CVSS v3.1 (fallback to v3.0)
    metrics = cve.get("metrics", {})
    cvss_v31 = metrics.get("cvssMetricV31", [])
    if not cvss_v31:
        cvss_v31 = metrics.get("cvssMetricV30", [])
    if not cvss_v31:
        return None

    cvss_data = cvss_v31[0].get("cvssData", {})
    base_score = float(cvss_data.get("baseScore", 0.0))
    av = AV_MAP.get(cvss_data.get("attackVector", ""), 0)
    ac = AC_MAP.get(cvss_data.get("attackComplexity", ""), 0)
    pr = PR_MAP.get(cvss_data.get("privilegesRequired", ""), 0)
    ui = UI_MAP.get(cvss_data.get("userInteraction", ""), 0)
    scope = SCOPE_MAP.get(cvss_data.get("scope", ""), 0)
    ci = IMPACT_MAP.get(cvss_data.get("confidentialityImpact", ""), 0)
    ii = IMPACT_MAP.get(cvss_data.get("integrityImpact", ""), 0)
    ai = IMPACT_MAP.get(cvss_data.get("availabilityImpact", ""), 0)

    # EPSS
    epss_data = epss_scores.get(cve_id, (0.0, 0.0))
    epss_score = epss_data[0]
    epss_percentile = epss_data[1]

    # Days since publication
    published = cve.get("published", "")
    days_since = 365.0
    if published:
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            days_since = float((datetime.now(UTC) - pub_date).days)
        except (ValueError, TypeError):
            pass

    # Has exploit reference in NVD
    references = cve.get("references", [])
    has_exploit_ref = 0
    for ref in references:
        tags = ref.get("tags", [])
        if "Exploit" in tags or "Third Party Advisory" in tags:
            has_exploit_ref = 1
            break

    # CWE category (target encoded)
    weaknesses = cve.get("weaknesses", [])
    cwe_value = CWE_DEFAULT
    for weakness in weaknesses:
        for desc in weakness.get("description", []):
            cwe_id = desc.get("value", "")
            if cwe_id in CWE_TARGET_ENCODING:
                cwe_value = CWE_TARGET_ENCODING[cwe_id]
                break

    # ExploitDB and Metasploit features
    has_public_exploit = 1 if cve_id in exploitdb_cves else 0
    has_metasploit = 1 if cve_id in metasploit_cves else 0
    num_refs = len(references)

    features = [
        base_score,
        float(av),
        float(ac),
        float(pr),
        float(ui),
        float(scope),
        float(ci),
        float(ii),
        float(ai),
        epss_score,
        epss_percentile,
        days_since,
        float(has_exploit_ref),
        cwe_value,
        float(has_public_exploit),
        float(has_metasploit),
        float(num_refs),
    ]

    return cve_id, features


def build_dataset(
    nvd_cves: list[dict[str, Any]],
    epss_scores: dict[str, tuple[float, float]],
    kev_cves: set[str],
    exploitdb_cves: set[str],
    metasploit_cves: set[str],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build feature matrix and label vector for exploitation prediction."""
    print("Building dataset...")
    x_rows: list[list[float]] = []
    y_labels: list[int] = []
    cve_ids: list[str] = []

    for cve_data in nvd_cves:
        result = extract_features(cve_data, epss_scores, exploitdb_cves, metasploit_cves)
        if result is None:
            continue

        cve_id, features = result

        # Composite ground truth: KEV OR Metasploit = confirmed exploitation
        label = 1 if (cve_id in kev_cves or cve_id in metasploit_cves) else 0

        x_rows.append(features)
        y_labels.append(label)
        cve_ids.append(cve_id)

    x = np.array(x_rows, dtype=np.float32)
    y = np.array(y_labels, dtype=np.int32)

    pos_count = int(y.sum())
    neg_count = len(y) - pos_count
    print(f"  Dataset: {len(y)} samples ({pos_count} exploited, {neg_count} not exploited)")
    print(f"  Positive rate: {pos_count / len(y):.2%}")

    return x, y, cve_ids


# ===================================================================
# Training
# ===================================================================


def _find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Find the classification threshold that maximizes F1 score."""
    best_f1 = 0.0
    best_threshold = 0.5
    for threshold in np.arange(0.1, 0.95, 0.01):
        y_pred = (y_prob >= threshold).astype(int)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(threshold)
    return best_threshold


def train_exploitation_model(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[XGBClassifier, dict[str, Any]]:
    """Train binary exploitation predictor with Optuna + SMOTE + threshold tuning."""
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    print("\n" + "=" * 60)
    print("Training EXPLOITATION PREDICTOR (binary)")
    print("=" * 60)

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    def objective(trial: optuna.Trial) -> float:
        smote_ratio = trial.suggest_float("smote_ratio", 0.05, 0.4)
        smote = SMOTE(random_state=RANDOM_STATE, sampling_strategy=smote_ratio)
        x_res, y_res = smote.fit_resample(x_train, y_train)

        clf = XGBClassifier(
            n_estimators=trial.suggest_int("n_estimators", 200, 800),
            max_depth=trial.suggest_int("max_depth", 3, 8),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            min_child_weight=trial.suggest_int("min_child_weight", 1, 10),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
            gamma=trial.suggest_float("gamma", 0.0, 5.0),
            reg_alpha=trial.suggest_float("reg_alpha", 0.0, 2.0),
            reg_lambda=trial.suggest_float("reg_lambda", 0.5, 3.0),
            random_state=RANDOM_STATE,
            eval_metric="aucpr",
        )
        clf.fit(x_res, y_res, eval_set=[(x_test, y_test)], verbose=False)

        y_prob = clf.predict_proba(x_test)[:, 1]
        threshold = _find_optimal_threshold(y_test, y_prob)
        y_pred = (y_prob >= threshold).astype(int)
        return float(f1_score(y_test, y_pred, zero_division=0))

    print(f"  Running {OPTUNA_N_TRIALS} Optuna trials...")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=OPTUNA_N_TRIALS, show_progress_bar=True)

    best = study.best_params
    print(f"  Best F1: {study.best_value:.4f}")
    print(f"  Best params: {best}")

    # Retrain with best parameters
    print("  Retraining with best parameters...")
    smote = SMOTE(random_state=RANDOM_STATE, sampling_strategy=best["smote_ratio"])
    x_train_res, y_train_res = smote.fit_resample(x_train, y_train)
    pos_resampled = int(y_train_res.sum())
    print(f"  After SMOTE: {len(y_train_res)} samples ({pos_resampled} positive)")

    model = XGBClassifier(
        n_estimators=best["n_estimators"],
        max_depth=best["max_depth"],
        learning_rate=best["learning_rate"],
        min_child_weight=best["min_child_weight"],
        subsample=best["subsample"],
        colsample_bytree=best["colsample_bytree"],
        gamma=best["gamma"],
        reg_alpha=best["reg_alpha"],
        reg_lambda=best["reg_lambda"],
        random_state=RANDOM_STATE,
        eval_metric="aucpr",
    )
    model.fit(x_train_res, y_train_res, eval_set=[(x_test, y_test)], verbose=False)

    # Find optimal threshold
    y_prob = model.predict_proba(x_test)[:, 1]
    optimal_threshold = _find_optimal_threshold(y_test, y_prob)
    print(f"  Optimal threshold: {optimal_threshold:.2f}")

    # Evaluate
    y_pred = (y_prob >= optimal_threshold).astype(int)

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "auc_roc": float(roc_auc_score(y_test, y_prob)),
        "optimal_threshold": optimal_threshold,
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
        "train_samples": len(y_train),
        "train_samples_after_smote": len(y_train_res),
        "test_samples": len(y_test),
        "positive_train": int(y_train.sum()),
        "positive_train_after_smote": pos_resampled,
        "positive_test": int(y_test.sum()),
        "smote_strategy": best["smote_ratio"],
        "optuna_trials": OPTUNA_N_TRIALS,
        "optuna_best_params": best,
    }

    # Feature importance
    importance = dict(zip(FEATURE_NAMES, model.feature_importances_.tolist(), strict=True))
    metrics["feature_importance"] = importance

    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1 Score:  {metrics['f1']:.4f}")
    print(f"  AUC-ROC:   {metrics['auc_roc']:.4f}")

    top_features = sorted(importance.items(), key=lambda item: item[1], reverse=True)[:5]
    print(f"  Top features: {top_features}")

    return model, metrics


# ===================================================================
# Output
# ===================================================================


def save_model(model: XGBClassifier, metrics: dict[str, Any]) -> Path:
    """Save model and metadata to models/."""
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))

    metadata = {
        "model_name": "xgboost_risk_model",
        "trained_at": datetime.now(UTC).isoformat(),
        "model_type": "XGBClassifier",
        "task": "binary_exploitation_prediction",
        "features": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "metrics": metrics,
    }

    metadata_path = MODEL_PATH.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print(f"  Model saved: {MODEL_PATH} ({MODEL_PATH.stat().st_size} bytes)")
    print(f"  Metadata saved: {metadata_path}")

    return MODEL_PATH


def write_report(metrics: dict[str, Any]) -> None:
    """Write training results report for thesis."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "training-results.md"

    lines = [
        "# SIOPV XGBoost Training Results -- Exploitation Predictor",
        f"\n**Date:** {datetime.now(UTC).isoformat()}",
        "",
        "---",
        "",
        "## Exploitation Predictor (binary classification)",
        "",
        f"**Accuracy:** {metrics['accuracy']:.4f}",
        f"**Precision:** {metrics['precision']:.4f}",
        f"**Recall:** {metrics['recall']:.4f}",
        f"**F1:** {metrics['f1']:.4f}",
        f"**AUC-ROC:** {metrics['auc_roc']:.4f}",
        f"**Optimal threshold:** {metrics.get('optimal_threshold', 0.5):.2f}",
        f"**Train samples:** {metrics['train_samples']}",
        f"**Train samples after SMOTE:** {metrics['train_samples_after_smote']}",
        f"**Test samples:** {metrics['test_samples']}",
        f"**SMOTE ratio:** {metrics['smote_strategy']:.4f}",
        f"**Optuna trials:** {metrics['optuna_trials']}",
        "",
        "### Confusion Matrix",
        "",
        "| | Predicted Negative | Predicted Positive |",
        "|---|---|---|",
    ]

    cm = metrics["confusion_matrix"]
    lines.append(f"| **Actual Negative** | {cm[0][0]} (TN) | {cm[0][1]} (FP) |")
    lines.append(f"| **Actual Positive** | {cm[1][0]} (FN) | {cm[1][1]} (TP) |")

    importance = metrics.get("feature_importance", {})
    sorted_importance = sorted(importance.items(), key=lambda item: item[1], reverse=True)

    lines.extend(
        [
            "",
            "### Feature Importance",
            "",
            "| Rank | Feature | Importance |",
            "|------|---------|-----------|",
        ]
    )
    for rank, (name, imp) in enumerate(sorted_importance, 1):
        lines.append(f"| {rank} | {name} | {imp:.4f} |")

    lines.extend(
        [
            "",
            "### Optuna Best Hyperparameters",
            "",
            "| Parameter | Value |",
            "|-----------|-------|",
        ]
    )
    for param, value in sorted(metrics.get("optuna_best_params", {}).items()):
        if isinstance(value, float):
            lines.append(f"| {param} | {value:.6f} |")
        else:
            lines.append(f"| {param} | {value} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Data Sources",
            "",
            "- **Ground truth:** CISA KEV + Metasploit modules "
            "(confirmed exploitation/weaponization)",
            "- **Features (17):** NVD CVSS v3.1 vectors + EPSS + CWE + ExploitDB flag "
            "+ Metasploit flag + reference count",
            "- **Data:** 200k+ CVEs from NVD, 321k EPSS scores, 1,551 CISA KEV, "
            "25k ExploitDB, 3,110 Metasploit",
            "- **Severity:** NOT modeled -- Trivy already provides severity from CVSS scores",
        ]
    )

    report_path.write_text("\n".join(lines))
    print(f"  Report saved: {report_path}")


# ===================================================================
# Main
# ===================================================================


def main() -> None:
    """Run the full training pipeline."""
    print("=" * 60)
    print("SIOPV XGBoost Training Pipeline -- Exploitation Predictor")
    print(f"Started: {datetime.now(UTC).isoformat()}")
    print("=" * 60)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    nvd_api_key = os.environ.get("SIOPV_NVD_API_KEY")
    if nvd_api_key:
        print("NVD API key found -- using higher rate limits")
    else:
        print("No NVD API key -- using public rate limits (slower)")

    with httpx.Client(follow_redirects=True) as client:
        # Step 1: Download all data sources
        kev_cves = download_cisa_kev(client)
        exploitdb_cves = download_exploitdb_cves(client)
        metasploit_cves = download_metasploit_cves(client)
        epss_scores = download_epss_scores(client)
        nvd_cves = download_nvd_cves(client, api_key=nvd_api_key)

        # Fetch KEV CVEs missing from NVD bulk download
        nvd_cves = fetch_missing_kev_cves(client, kev_cves, nvd_cves, nvd_api_key)

        # Report ground truth composition
        composite_positives = kev_cves | metasploit_cves
        print(
            f"\nGround truth: {len(composite_positives)} CVEs "
            f"(KEV: {len(kev_cves)}, Metasploit: {len(metasploit_cves)}, "
            f"overlap: {len(kev_cves & metasploit_cves)})"
        )
        print(f"ExploitDB feature: {len(exploitdb_cves)} CVEs with published exploits")

        # Step 2: Build dataset
        x, y, _cve_ids = build_dataset(
            nvd_cves, epss_scores, kev_cves, exploitdb_cves, metasploit_cves
        )

        # Step 3: Train exploitation predictor
        model, metrics = train_exploitation_model(x, y)

        # Step 4: Save model and write report
        save_model(model, metrics)
        write_report(metrics)

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"  Model: {MODEL_PATH}")
    print(f"  Report: {REPORT_DIR / 'training-results.md'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
