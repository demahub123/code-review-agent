import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from agent import tools, memory

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
MAX_STEPS = 20

TOOL_FUNCTIONS = {
    "read_file": tools.read_file,
    "run_tests": tools.run_tests,
    "apply_patch": tools.apply_patch,
    "search_memory": memory.search_memory,
}

SYSTEM_PROMPT = """You are a code review and bug triage agent for Python projects.
Work step by step using your tools:
1. Run the tests to see what fails.
2. Call search_memory with a short description of the failures to check for similar past cases. Treat the results as hints, not facts.
3. Read the relevant source file to find the cause. Never edit test files.
4. Fix the bugs with patches (apply_patch), using file paths exactly as they appear inside the project folder (for example sample_project2/utils.py).
5. Run the tests again to verify the fix.
6. If a patch fails or tests still fail, read the error, reconsider, and try a different fix.
When all tests pass, stop and give a short report: the bugs, the fixes, and the evidence."""

client = genai.Client(http_options=types.HttpOptions(timeout=60000))


def call_llm(contents, config, retries=2):
    """Call the LLM, retrying if the server fails (we saw 504 errors earlier)."""
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(
                model=MODEL, contents=contents, config=config
            )
        except Exception as e:
            print(f"  LLM error (attempt {attempt + 1}): {e}")
            time.sleep(2)
    return None


def run_agent(goal):
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=list(TOOL_FUNCTIONS.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=goal)])]

    first_failure = ""
    last_tests = ""
    patches = 0

    def finish(report, steps):
        success = "passed" in last_tests and "failed" not in last_tests
        memory.save_episode({
            "project": tools._sandbox.name,
            "failure_text": first_failure[:600],
            "report": report[:800],
            "success": success,
            "steps": steps,
            "patches": patches,
        })
        print(f"\nSaved to memory: success={success}, steps={steps}, patches={patches}")
        return {"success": success, "steps": steps, "patches": patches}

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- Step {step} ---")
        response = call_llm(contents, config)
        if response is None:
            print("Stopping: the LLM is unavailable.")
            return {"success": False, "steps": step, "patches": patches}

        contents.append(response.candidates[0].content)

        if not response.function_calls:
            print("AGENT REPORT:", response.text)
            return finish(response.text or "", step)

        result_parts = []
        for call in response.function_calls:
            args = dict(call.args)
            print(f"ACT: {call.name}({args})")
            func = TOOL_FUNCTIONS.get(call.name)
            try:
                result = func(**args) if func else f"ERROR: unknown tool {call.name}"
            except Exception as e:
                result = f"ERROR: tool crashed: {e}"
            print("RESULT:", result[:300])

            if call.name == "run_tests":
                last_tests = result
                if not first_failure:
                    first_failure = result
            if call.name == "apply_patch" and result.startswith("OK"):
                patches += 1

            result_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result}
                )
            )
        contents.append(types.Content(role="user", parts=result_parts))

    print("\nStopped: reached MAX_STEPS without finishing.")
    return finish("Stopped at the step limit without finishing.", MAX_STEPS)