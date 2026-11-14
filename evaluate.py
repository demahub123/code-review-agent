import contextlib
import csv
import io
import subprocess
import sys
import time
from pathlib import Path

import agent.agent as agent_module
from agent import memory, tools

PROJECTS = ["sample_project", "sample_project2", "sample_project3", "sample_project4"]
CONDITIONS = ["baseline", "memory", "fault"]
RESULTS = Path("results.csv")
EVAL_MEMORY = Path("eval_memory.json")
TRACES = Path("traces")
FIELDS = ["condition", "project", "run", "success", "steps", "patches",
          "tool_errors", "seconds", "llm_error"]
PAUSE = 5  # seconds between runs, to be gentle on the free tier


def reset_bugs():
    subprocess.run(["git", "checkout", "--"] + PROJECTS, capture_output=True)


def run_one(condition, project, use_memory, inject_fault):
    """Run the agent once on a freshly reset project. Returns (result, trace, seconds)."""
    reset_bugs()
    tools.set_sandbox(project)
    tools.inject_patch_failure(1 if inject_fault else 0)
    agent_module.USE_MEMORY = use_memory
    memory.EXCLUDE_PROJECT = project
    goal = (
        f"The Python project in the folder '{project}' may contain bugs. "
        "Run its tests. If any fail, find and fix all the bugs, then verify the fixes."
    )
    buffer = io.StringIO()
    start = time.time()
    try:
        with contextlib.redirect_stdout(buffer):
            result = agent_module.run_agent(goal)
    except Exception as e:
        buffer.write(f"\nCRASH: {e}")
        result = {"success": False, "steps": 0, "patches": 0,
                  "tool_errors": 0, "llm_error": True}
    seconds = round(time.time() - start, 1)
    reset_bugs()
    return result, buffer.getvalue(), seconds


def already_done():
    if not RESULTS.exists():
        return set()
    with RESULTS.open(newline="", encoding="utf-8") as f:
        return {(r["condition"], r["project"], int(r["run"])) for r in csv.DictReader(f)}


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    memory.MEMORY_FILE = EVAL_MEMORY
    TRACES.mkdir(exist_ok=True)

    if "memory" in CONDITIONS and not EVAL_MEMORY.exists():
        print("Seeding memory with one run per project (not recorded)...")
        for project in PROJECTS:
            result, _, _ = run_one("seed", project, use_memory=True, inject_fault=False)
            print(f"  seed {project}: success={result['success']}")
            time.sleep(PAUSE)

    done = already_done()
    new_file = not RESULTS.exists()
    with RESULTS.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for run in range(1, runs + 1):
            for project in PROJECTS:
                for condition in CONDITIONS:
                    if (condition, project, run) in done:
                        continue
                    result, trace, seconds = run_one(
                        condition, project,
                        use_memory=(condition == "memory"),
                        inject_fault=(condition == "fault"),
                    )
                    (TRACES / f"{condition}_{project}_run{run}.txt").write_text(
                        trace, encoding="utf-8")
                    writer.writerow({
                        "condition": condition, "project": project, "run": run,
                        "success": result["success"], "steps": result["steps"],
                        "patches": result["patches"],
                        "tool_errors": result["tool_errors"],
                        "seconds": seconds, "llm_error": result["llm_error"],
                    })
                    f.flush()
                    print(f"{condition:9} {project:16} run {run}: "
                          f"success={result['success']} steps={result['steps']} "
                          f"patches={result['patches']} errors={result['tool_errors']} "
                          f"{seconds}s")
                    time.sleep(PAUSE)
    print("\nDone. Results saved to results.csv, traces saved in the traces folder.")


if __name__ == "__main__":
    main()