import subprocess
import sys
from pathlib import Path

_sandbox = Path("sample_project").resolve()


def set_sandbox(path: str) -> None:
    """Set the only folder the agent may read, test or edit. Not given to the LLM."""
    global _sandbox
    _sandbox = Path(path).resolve()


def _in_sandbox(path: str) -> bool:
    p = Path(path).resolve()
    return p == _sandbox or _sandbox in p.parents


def read_file(path: str) -> str:
    """Read a text file inside the project folder and return its contents."""
    if not _in_sandbox(path):
        return f"ERROR: refusing to read outside the sandbox: {path}"
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"ERROR: file not found: {path}"
    except Exception as e:
        return f"ERROR: {e}"


def run_tests(project_dir: str, timeout: int = 30) -> str:
    """Run pytest inside project_dir and return the output."""
    if not _in_sandbox(project_dir):
        return f"ERROR: refusing to run tests outside the sandbox: {project_dir}"
    timeout = min(timeout, 60)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=short"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"ERROR: tests timed out after {timeout} seconds"
    except Exception as e:
        return f"ERROR: {e}"


def apply_patch(path: str, old_text: str, new_text: str) -> str:
    """Replace old_text with new_text in one file inside the project folder."""
    if not _in_sandbox(path):
        return f"ERROR: refusing to edit outside the sandbox: {path}"
    try:
        file_path = Path(path).resolve()
        content = file_path.read_text(encoding="utf-8")
        count = content.count(old_text)
        if count == 0:
            return "ERROR: old_text not found, no changes made"
        if count > 1:
            return f"ERROR: old_text appears {count} times, be more specific"
        file_path.write_text(content.replace(old_text, new_text), encoding="utf-8")
        return f"OK: patched {path}"
    except Exception as e:
        return f"ERROR: {e}"