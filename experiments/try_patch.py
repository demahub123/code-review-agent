from agent.tools import run_tests, apply_patch

print("BEFORE:")
print(run_tests("sample_project"))

print(apply_patch("sample_project/calculator.py", "len(numbers) + 1", "len(numbers)"))

print("AFTER:")
print(run_tests("sample_project"))

print("SANDBOX TEST:")
print(apply_patch("agent/tools.py", "read_file", "hacked"))