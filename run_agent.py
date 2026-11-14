import sys
from agent.tools import set_sandbox
from agent.agent import run_agent

project = sys.argv[1] if len(sys.argv) > 1 else "sample_project"
set_sandbox(project)

run_agent(
    f"The Python project in the folder '{project}' may contain bugs. "
    "Run its tests. If any fail, find and fix all the bugs, then verify the fixes."
)