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