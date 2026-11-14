import subprocess
import sys
from pathlib import Path


def read_file(path: str) -> str:
    """Read a text file and return its contents."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"ERROR: file not found: {path}"
    except Exception as e:
        return f"ERROR: {e}"


def run_tests(project_dir: str, timeout: int = 30) -> str:
    """Run pytest inside project_dir and return the output."""
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

def apply_patch(path: str, old_text: str, new_text: str, sandbox: str = "sample_project") -> str:
    """Replace old_text with new_text in one file. Only works inside the sandbox folder."""
    try:
        file_path = Path(path).resolve()
        sandbox_path = Path(sandbox).resolve()
        if sandbox_path not in file_path.parents:
            return f"ERROR: refusing to edit outside the sandbox: {path}"
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