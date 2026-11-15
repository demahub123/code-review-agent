import inspect

import pytest

from agent import tools


@pytest.fixture
def sandbox(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "code.py").write_text("x = 1\ny = 1\n", encoding="utf-8")
    (project / "test_code.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    outside = tmp_path / "secret.txt"
    outside.write_text("SECRET", encoding="utf-8")
    sibling = tmp_path / "proj_evil"
    sibling.mkdir()
    (sibling / "data.txt").write_text("EVIL", encoding="utf-8")
    tools.set_sandbox(str(project))
    tools.inject_patch_failure(0)
    return project, outside, sibling


def test_read_inside_sandbox_works(sandbox):
    project, _, _ = sandbox
    assert "x = 1" in tools.read_file(str(project / "code.py"))


def test_read_outside_sandbox_refused(sandbox):
    _, outside, _ = sandbox
    result = tools.read_file(str(outside))
    assert result.startswith("ERROR") and "SECRET" not in result


def test_read_path_traversal_refused(sandbox):
    project, _, _ = sandbox
    result = tools.read_file(str(project / ".." / "secret.txt"))
    assert result.startswith("ERROR") and "SECRET" not in result


def test_read_sibling_folder_with_similar_name_refused(sandbox):
    _, _, sibling = sandbox
    result = tools.read_file(str(sibling / "data.txt"))
    assert result.startswith("ERROR") and "EVIL" not in result


def test_patch_outside_sandbox_refused_and_file_unchanged(sandbox):
    _, outside, _ = sandbox
    result = tools.apply_patch(str(outside), "SECRET", "HACKED")
    assert result.startswith("ERROR")
    assert outside.read_text(encoding="utf-8") == "SECRET"


def test_patch_valid_applies(sandbox):
    project, _, _ = sandbox
    result = tools.apply_patch(str(project / "code.py"), "x = 1", "x = 2")
    assert result.startswith("OK")
    assert "x = 2" in (project / "code.py").read_text(encoding="utf-8")


def test_patch_text_not_found_changes_nothing(sandbox):
    project, _, _ = sandbox
    before = (project / "code.py").read_text(encoding="utf-8")
    result = tools.apply_patch(str(project / "code.py"), "does not exist", "z")
    assert result.startswith("ERROR")
    assert (project / "code.py").read_text(encoding="utf-8") == before


def test_patch_ambiguous_text_changes_nothing(sandbox):
    project, _, _ = sandbox
    before = (project / "code.py").read_text(encoding="utf-8")
    result = tools.apply_patch(str(project / "code.py"), "= 1", "= 9")
    assert result.startswith("ERROR")
    assert (project / "code.py").read_text(encoding="utf-8") == before


def test_run_tests_outside_sandbox_refused(sandbox):
    _, outside, _ = sandbox
    result = tools.run_tests(str(outside.parent))
    assert result.startswith("ERROR")


def test_run_tests_inside_sandbox_works(sandbox):
    project, _, _ = sandbox
    assert "1 passed" in tools.run_tests(str(project))


def test_run_tests_timeout_is_enforced(sandbox):
    project, _, _ = sandbox
    slow = project / "slow"
    slow.mkdir()
    (slow / "test_slow.py").write_text(
        "import time\n\ndef test_slow():\n    time.sleep(10)\n", encoding="utf-8"
    )
    result = tools.run_tests(str(slow), timeout=1)
    assert "timed out" in result


def test_injected_patch_failure_fails_once_then_recovers(sandbox):
    project, _, _ = sandbox
    tools.inject_patch_failure(1)
    first = tools.apply_patch(str(project / "code.py"), "x = 1", "x = 2")
    assert first.startswith("ERROR") and "simulated" in first
    assert "x = 1" in (project / "code.py").read_text(encoding="utf-8")
    second = tools.apply_patch(str(project / "code.py"), "x = 1", "x = 2")
    assert second.startswith("OK")


def test_llm_cannot_see_or_change_the_sandbox_setting():
    for fn in (tools.read_file, tools.run_tests, tools.apply_patch):
        assert "sandbox" not in inspect.signature(fn).parameters