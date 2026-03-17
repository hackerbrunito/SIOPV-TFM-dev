# Streamlit — Context7 Cache (Pre-Wave Research)

> Queried: 2026-03-17 | Source: Streamlit docs + web research

## st.dialog API

### Signature
```python
@st.dialog(title, *, width="small", dismissible=True, icon=None, on_dismiss="ignore")
def my_dialog(param):
    ...
```

### Parameters
- **title** (str): Modal heading, supports GitHub-flavored Markdown
- **width**: `"small"` (500px), `"medium"` (750px), `"large"` (1280px)
- **dismissible** (bool): Whether user can close via click-outside/ESC/X
- **icon** (str|None): Emoji or Material Symbol (e.g., `:material/thumb_up:`)
- **on_dismiss**: `"ignore"` | `"rerun"` | callable

### Usage Pattern
```python
@st.dialog("Review Vulnerability")
def review_dialog(vuln_id: str):
    st.write(f"Reviewing: {vuln_id}")
    decision = st.radio("Decision", ["Approve", "Reject", "Escalate"])
    if st.button("Submit"):
        st.session_state.decision = decision
        st.rerun()

if st.button("Review"):
    review_dialog("CVE-2026-1234")
```

### Key Behaviors
- Inherits from `st.fragment` — only dialog function reruns on widget interaction
- Only ONE dialog can be open at a time
- `st.sidebar` NOT supported inside dialog
- Close via `st.rerun()` or user dismiss
- State management via `st.session_state`

## st.fragment API
```python
@st.fragment(run_every=None)
def my_component():
    ...  # reruns independently from full script
```

## Best Practices

1. **Session State for dialog results** — store decisions in `st.session_state`
2. **Close with st.rerun()** — after state update, rerun to close dialog and reflect changes
3. **One dialog at a time** — design UI flow accordingly
4. **Fragment for performance** — use `@st.fragment` for components that update frequently
5. **Additive side effects** — dialog reruns are additive; manage state carefully
