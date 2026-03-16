# STAGE-3 Research: Streamlit HITL + LIME Visualization — State of the Art
**Researcher:** researcher-streamlit-lime
**Timestamp:** 2026-03-11-175427
**Status:** COMPLETE

---

## 1. Streamlit 1.x Verified Patterns

### 1.1 Polling SQLite with `st.fragment(run_every=...)`

**Preferred pattern** (verified via Context7 `/streamlit/docs`):

```python
import streamlit as st
import sqlite3
import time

@st.fragment(run_every="15s")
def poll_pending_reviews():
    """Poll SQLite for new escalated vulnerabilities every 15s."""
    with sqlite3.connect("siopv_checkpoints.db") as conn:
        rows = conn.execute(
            "SELECT thread_id, vuln_id, severity, created_at "
            "FROM escalations WHERE status='pending' ORDER BY created_at"
        ).fetchall()
    st.session_state.pending_reviews = rows
    st.metric("Pending Reviews", len(rows))

poll_pending_reviews()
```

Key: `@st.fragment(run_every=...)` reruns **only that fragment** on schedule — no full page rerun.
Accepts: `"10s"`, `"1m"`, `timedelta` objects, or `int` (seconds).

**Alternative** (full page, simpler):
```python
time.sleep(30)
st.rerun()
```
Avoid in production — blocks the thread and reruns entire page.

### 1.2 Session State Machine for HITL Approve/Reject/Escalate

```python
# Initialize state machine
if "review_state" not in st.session_state:
    st.session_state.review_state = {
        "stage": "list",          # list | reviewing | decided
        "current_thread_id": None,
        "decision": None,          # approve | reject | escalate
        "reviewer_id": None,
        "timestamp": None,
    }

def render_review_panel(thread_id: str, vuln_data: dict):
    rs = st.session_state.review_state

    st.subheader(f"Vulnerability: {vuln_data['vuln_id']}")
    st.write(f"Severity: **{vuln_data['severity']}**")
    st.write(f"Score: {vuln_data['risk_score']:.3f}")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Approve", type="primary"):
            rs["stage"] = "decided"
            rs["decision"] = "approve"
            rs["current_thread_id"] = thread_id
            rs["timestamp"] = time.time()
            st.rerun()

    with col2:
        if st.button("❌ Reject"):
            rs["stage"] = "decided"
            rs["decision"] = "reject"
            rs["current_thread_id"] = thread_id
            rs["timestamp"] = time.time()
            st.rerun()

    with col3:
        if st.button("⬆ Escalate (24h)"):
            rs["stage"] = "decided"
            rs["decision"] = "escalate"
            rs["current_thread_id"] = thread_id
            rs["timestamp"] = time.time()
            st.rerun()
```

### 1.3 Auth Integration — Token/OpenFGA Gate

Streamlit 1.x exposes **request headers** via `st.context.headers` (verified Context7):

```python
import streamlit as st

def require_auth() -> str:
    """Gate the dashboard behind an Authorization header or token cookie."""
    auth_header = st.context.headers.get("Authorization", "")
    token_cookie = st.context.cookies.get("siopv_token", "")

    token = auth_header.replace("Bearer ", "") or token_cookie

    if not token:
        st.error("Authentication required. Please login.")
        st.stop()

    # Call OpenFGA / validate JWT here
    reviewer_id = validate_token(token)  # your validation function
    if not reviewer_id:
        st.error("Invalid or expired token.")
        st.stop()

    return reviewer_id

# Top of every page:
reviewer_id = require_auth()
```

For OIDC/OAuth providers, Streamlit 1.x also has native `st.login()`:
```python
if not st.user.is_logged_in:
    st.login("keycloak")  # configured in .streamlit/secrets.toml
st.write(f"Logged in as: {st.user.name}")
st.logout()
```

### 1.4 Port Binding via Environment Variable

**Streamlit env var convention**: `STREAMLIT_SERVER_PORT`

```bash
# In your launch wrapper:
export STREAMLIT_SERVER_PORT=${DASHBOARD_PORT:-8501}
streamlit run dashboard.py
```

Or read in Python and pass via CLI:
```python
# entrypoint.py
import os, subprocess, sys
port = os.environ.get("DASHBOARD_PORT", "8501")
subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard.py",
                "--server.port", port])
```

Note: `DASHBOARD_PORT` → must be mapped to `STREAMLIT_SERVER_PORT` or `--server.port` CLI flag.
Direct `DASHBOARD_PORT` is not recognized by Streamlit — always translate.

### 1.5 Timeout Countdown + Cascade UI

```python
@st.fragment(run_every="60s")
def render_timeout_status(created_at: float, thresholds: dict):
    """Display escalation cascade timer."""
    elapsed = time.time() - created_at
    remaining_4h  = max(0, 4*3600 - elapsed)
    remaining_8h  = max(0, 8*3600 - elapsed)
    remaining_24h = max(0, 24*3600 - elapsed)

    col1, col2, col3 = st.columns(3)
    with col1:
        pct = 1 - (remaining_4h / (4*3600))
        st.progress(min(pct, 1.0), text=f"L1 (4h): {int(remaining_4h//60)}m left")
    with col2:
        pct = 1 - (remaining_8h / (8*3600))
        st.progress(min(pct, 1.0), text=f"L2 (8h): {int(remaining_8h//60)}m left")
    with col3:
        pct = 1 - (remaining_24h / (24*3600))
        st.progress(min(pct, 1.0), text=f"L3 (24h): {int(remaining_24h//60)}m left")

    if elapsed >= 24*3600:
        st.error("⚠️ AUTO-ESCALATED: 24h limit reached")
    elif elapsed >= 8*3600:
        st.warning("⚠️ L3 escalation: no response in 8h")
    elif elapsed >= 4*3600:
        st.warning("⚠️ L2 escalation: no response in 4h")
```

---

## 2. LIME Verified Patterns

### 2.1 LimeTabularExplainer — Current API (verified via `lime-ml.readthedocs.io`)

```python
from lime.lime_tabular import LimeTabularExplainer
import numpy as np

# Constructor
explainer = LimeTabularExplainer(
    training_data=X_train,                   # np.ndarray (n_samples, n_features)
    mode="classification",                    # "classification" | "regression"
    feature_names=feature_names,             # list[str]
    class_names=["low", "medium", "high"],   # list[str]
    categorical_features=cat_feature_indices, # list[int]
    categorical_names=cat_feature_names,     # dict[int, list[str]]
    discretize_continuous=True,              # quartile discretization
    random_state=42,
)
```

### 2.2 explain_instance — Full Signature

```python
explanation = explainer.explain_instance(
    data_row=instance,           # np.ndarray 1D (single sample)
    predict_fn=model.predict_proba,  # callable: array → array of probabilities
    labels=(1,),                 # which class labels to explain (default: (1,))
    top_labels=None,             # if set, explains top N predicted labels
    num_features=10,             # max features in explanation
    num_samples=5000,            # perturbation samples for local linear model
    distance_metric="euclidean",
)
```

### 2.3 Visualization — as_pyplot_figure

```python
import matplotlib.pyplot as plt

# Get matplotlib figure
fig = explanation.as_pyplot_figure(label=1)   # label = class index

# Fine-tune (optional)
fig.set_size_inches(10, 6)
fig.tight_layout()
```

### 2.4 Other Output Formats

```python
# List of (feature_name, weight) tuples — for custom rendering
feature_weights = explanation.as_list(label=1)
# e.g.: [("cvss_score > 7.0", 0.42), ("has_exploit = True", 0.31), ...]

# HTML — for notebook or raw embed
html = explanation.as_html()

# Prediction probabilities
probs = explanation.predict_proba
```

---

## 3. Integration Patterns — Streamlit + LIME

### 3.1 Embedding LIME Bar Chart in Dashboard

**st.pyplot (preferred for matplotlib)**:
```python
import streamlit as st
import matplotlib.pyplot as plt
from lime.lime_tabular import LimeTabularExplainer

def render_lime_explanation(
    explainer: LimeTabularExplainer,
    instance: np.ndarray,
    predict_fn,
    label: int = 1,
    num_features: int = 10,
):
    with st.spinner("Generating LIME explanation..."):
        exp = explainer.explain_instance(
            instance, predict_fn,
            num_features=num_features,
            num_samples=3000,   # reduce for speed in live dashboards
        )

    st.subheader("Feature Contributions (LIME)")

    # Option A: matplotlib figure
    fig = exp.as_pyplot_figure(label=label)
    fig.set_size_inches(9, 5)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)  # IMPORTANT: prevent memory leak in long-running apps

    # Option B: custom bar chart from weights (Streamlit-native)
    weights = exp.as_list(label=label)
    feature_names_w = [w[0] for w in weights]
    values = [w[1] for w in weights]
    colors = ["#2ecc71" if v > 0 else "#e74c3c" for v in values]

    import pandas as pd
    df = pd.DataFrame({"feature": feature_names_w, "weight": values})
    st.bar_chart(df.set_index("feature"))
```

**Note on `plt.close(fig)`**: Critical for Streamlit apps — matplotlib figures accumulate in memory across reruns if not closed.

### 3.2 Full HITL Panel with LIME (Composite)

```python
def render_hitl_review_page(thread_id: str, vuln: dict, explainer, model, X_train):
    st.title(f"Review: {vuln['vuln_id']}")

    # Timeout status
    render_timeout_status(vuln["created_at"], thresholds={4, 8, 24})

    # Vulnerability details
    with st.expander("Vulnerability Details", expanded=True):
        st.json(vuln)

    # LIME explanation
    with st.expander("ML Explanation (LIME)", expanded=True):
        instance = np.array(vuln["feature_vector"])
        render_lime_explanation(explainer, instance, model.predict_proba)

    # Decision buttons
    st.divider()
    render_review_panel(thread_id, vuln)
```

### 3.3 LangGraph SQLite Resume Pattern

```python
# After reviewer clicks Approve/Reject:
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

def resume_langgraph(thread_id: str, decision: str, notes: str = ""):
    """Resume a paused LangGraph graph after HITL decision."""
    with SqliteSaver.from_conn_string("siopv_checkpoints.db") as checkpointer:
        config = {"configurable": {"thread_id": thread_id}}
        # Resume the interrupted graph with human decision
        result = graph.invoke(
            Command(resume={"decision": decision, "reviewer_notes": notes}),
            config=config,
        )
    return result
```

---

## 4. Libraries Verified

| Library | Context7 ID | WebSearch | Status |
|---------|-------------|-----------|--------|
| Streamlit 1.x | `/streamlit/docs` (1477 snippets, score 85.78) | ✅ | Verified — `st.fragment`, `st.rerun`, `st.context`, `st.user` |
| LIME (lime-ml) | Not in Context7 (confused with Lime Elements) | ✅ readthedocs.io fetched | Verified — `LimeTabularExplainer`, `explain_instance`, `as_pyplot_figure` |

**Context7 queries performed:**
1. `st.rerun` + polling + session state patterns
2. `st.fragment` auto-refresh + `run_every` parameter
3. Auth: `st.user`, `st.context.headers`, `st.login()`

**WebSearch cross-checks performed:**
1. Streamlit polling SQLite HITL patterns 2025
2. LIME tabular explainer + XGBoost 2024/2025
3. Streamlit port env var configuration
4. LangGraph interrupt/resume + Streamlit HITL 2025/2026
5. LIME + Streamlit st.pyplot integration

---

## 5. Key Findings Summary

1. **`@st.fragment(run_every="Xs")`** is the correct 1.x pattern for polling — not `time.sleep` + `st.rerun()`. Fragments update independently without full page reruns.

2. **Port mapping**: `DASHBOARD_PORT` is not a native Streamlit env var. Must translate to `STREAMLIT_SERVER_PORT` or `--server.port` CLI flag in a launch wrapper.

3. **Auth gate**: Use `st.context.headers.get("Authorization")` to read bearer tokens for programmatic OpenFGA validation. Native `st.login()` supports OIDC (Keycloak). Both patterns are available in 1.x.

4. **LIME API is stable**: `LimeTabularExplainer` constructor, `explain_instance`, and `as_pyplot_figure(label=N)` have not changed. Always call `plt.close(fig)` after `st.pyplot()` to prevent memory leaks.

5. **LIME bar chart embedding**: `st.pyplot(fig, use_container_width=True)` is the canonical integration. Alternative: extract `exp.as_list(label=1)` and render with `st.bar_chart` for a native Streamlit look.

6. **LangGraph resume**: Use `Command(resume={...})` with `SqliteSaver` to resume interrupted graphs. The Streamlit app reads checkpoint state from SQLite and writes the decision back via graph resume — no direct state mutation.

7. **Session state machine**: Track `stage` (list → reviewing → decided), `current_thread_id`, `decision`, `reviewer_id` in `st.session_state`. Call `st.rerun()` on state transitions to redraw immediately.

8. **Timeout cascade UI**: `@st.fragment(run_every="60s")` + `st.progress()` gives a live countdown without blocking. Auto-escalation logic should live in LangGraph, not Streamlit (Streamlit just reads state).

9. **Memory management**: Long-running Streamlit apps must `plt.close(fig)` after every LIME plot render to avoid unbounded memory growth.

10. **HITL + LangGraph is well-documented (Feb 2026)**: Multiple production articles confirm the `interrupt()` + Streamlit frontend + SQLite checkpointer pattern is production-ready.

---

## Sources

- [Streamlit Docs — st.fragment](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)
- [LIME readthedocs](https://lime-ml.readthedocs.io/en/latest/lime.html)
- [LangGraph HITL patterns — Medium 2025](https://medium.com/the-advanced-school-of-ai/human-in-the-loop-with-langgraph-mastering-interrupts-and-commands-9e1cf2183ae3)
- [LangGraph + Streamlit HITL — MarkTechPost Feb 2026](https://www.marktechpost.com/2026/02/16/how-to-build-human-in-the-loop-plan-and-execute-ai-agents-with-explicit-user-approval-using-langgraph-and-streamlit/)
- [LIME + Streamlit forum thread](https://discuss.streamlit.io/t/how-to-print-lime-output-on-python-web-application-using-streamlit/1133)
- [Streamlit config env vars — Restack](https://www.restack.io/docs/streamlit-knowledge-streamlit-environment-variables-guide)
- [XGBoost + LIME tutorial](https://xgboosting.com/explain-xgboost-predictions-with-lime/)
