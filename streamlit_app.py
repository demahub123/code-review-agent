from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json

import streamlit as st

from agent import memory, tools
from agent.agent import run_agent

ROOT = Path(__file__).resolve().parent
st.set_page_config(
    page_title="Code Review Agent",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ Code Review and Bug Triage Agent")
st.caption("An AI agent that investigates Python test failures, applies fixes, and verifies the result.")

def project_folders():
    candidates = []
    for path in ROOT.iterdir():
        if path.is_dir() and path.name.startswith("sample_project"):
            candidates.append(path.name)
    return sorted(candidates)

def load_csv(path):
    try:
        import pandas as pd
        return pd.read_csv(path)
    except Exception:
        return None

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Open section",
        ["Dashboard", "Run Code Review", "Agent Memory", "Evaluation"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Gemini-powered • Local execution")
    st.caption("The agent edits files in the selected project folder.")

if page == "Dashboard":
    st.subheader("Project overview")
    projects = project_folders()
    c1, c2, c3 = st.columns(3)
    c1.metric("Sample projects", len(projects))
    c2.metric("Agent tools", 4)
    c3.metric("Evaluation runs", 36)

    st.markdown("### What the agent does")
    left, right = st.columns(2)
    with left:
        st.markdown("""
        **Investigate**
        - Runs the project's pytest tests
        - Reads relevant source files
        - Searches memory for similar bug symptoms
        """)
    with right:
        st.markdown("""
        **Repair and verify**
        - Applies exact-match code patches
        - Runs tests again
        - Saves general lessons from successful runs
        """)
    st.info("Choose **Run Code Review** in the sidebar to start the agent on one of the sample projects.")
    st.warning("The agent edits files in place. Keep backups of important projects and only run it on code you trust.")

elif page == "Run Code Review":
    st.subheader("Run a code review")
    projects = project_folders()
    if not projects:
        st.error("No sample_project folders were found beside streamlit_app.py.")
    else:
        selected = st.selectbox("Choose a project", projects)
        st.write(f"Selected folder: `{selected}`")
        st.warning("Running the agent can modify files in the selected folder. Restore sample projects from Git after experiments.")
        inject_failure = st.checkbox("Simulate a first-patch failure (for recovery testing)")
        run = st.button("▶ Run Agent", type="primary", width='stretch')

        if run:
            output = StringIO()
            try:
                with st.spinner("The agent is investigating the project. This may take a few minutes..."):
                    tools.set_sandbox(selected)
                    if inject_failure:
                        tools.inject_patch_failure(1)
                    with redirect_stdout(output):
                        metrics = run_agent(
                            f"The Python project in the folder '{selected}' may contain bugs. "
                            "Run its tests. If any fail, find and fix all the bugs, then verify the fixes."
                        )
                st.session_state["last_output"] = output.getvalue()
                st.session_state["last_metrics"] = metrics
                st.session_state["last_project"] = selected
            except Exception as exc:
                st.error(f"Agent run failed: {exc}")

        if "last_output" in st.session_state:
            st.divider()
            st.markdown(f"### Latest run: `{st.session_state.get('last_project', '')}`")
            metrics = st.session_state.get("last_metrics", {})
            a, b, c, d = st.columns(4)
            a.metric("Result", "Passed" if metrics.get("success") else "Not passed")
            b.metric("Steps", metrics.get("steps", "—"))
            c.metric("Patches", metrics.get("patches", "—"))
            d.metric("Tool errors", metrics.get("tool_errors", "—"))
            st.text_area("Agent activity and final report", st.session_state["last_output"], height=420)

elif page == "Agent Memory":
    st.subheader("Agent memory")
    episodes = memory.load()
    if not episodes:
        st.info("No saved episodes yet. Run the agent to create its first memory entry.")
    else:
        st.metric("Saved episodes", len(episodes))
        for index, episode in enumerate(reversed(episodes), start=1):
            label = f"{episode.get('project', 'Project')} — {'Successful' if episode.get('success') else 'Unsuccessful'}"
            with st.expander(f"{index}. {label}"):
                st.write(f"Steps: {episode.get('steps', '—')}  |  Patches: {episode.get('patches', '—')}")
                if episode.get("failure_text"):
                    st.markdown("**Initial test output**")
                    st.code(episode["failure_text"])
                if episode.get("report"):
                    st.markdown("**Final report**")
                    st.write(episode["report"])
                lessons = episode.get("lessons", [])
                if lessons:
                    st.markdown("**Lessons saved**")
                    for lesson in lessons:
                        st.write(f"- {lesson}")

elif page == "Evaluation":
    st.subheader("Evaluation results")
    summary = load_csv(ROOT / "summary.csv")
    results = load_csv(ROOT / "results.csv")
    if summary is not None:
        st.markdown("**Summary metrics**")
        st.dataframe(summary, width='stretch', hide_index=True)
    else:
        st.info("summary.csv was not found or could not be read.")
    if results is not None:
        st.markdown("**Recorded evaluation runs**")
        st.dataframe(results, width='stretch', hide_index=True)
    for chart in ["success_rate.png", "steps_by_project.png", "patches_by_project.png"]:
        image_path = ROOT / "charts" / chart
        if image_path.exists():
            st.markdown(f"**{chart.replace('_', ' ').replace('.png', '').title()}**")
            st.image(str(image_path), width='stretch')
    st.caption("These are the saved evaluation results from the project's completed experiments.")
