import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from agent import tools

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
MAX_STEPS = 8

TOOL_FUNCTIONS = {
    "read_file": tools.read_file,
    "run_tests": tools.run_tests,
    "apply_patch": tools.apply_patch,
}

SYSTEM_PROMPT = """You are a code review and bug triage agent for Python projects.
Work step by step using your tools:
1. Run the tests to see what fails.
2. Read the relevant source file to find the cause. Never edit test files.
3. Fix the bug with a minimal patch (apply_patch), using file paths like sample_project/calculator.py.
4. Run the tests again to verify the fix.
5. If a patch fails or tests still fail, read the error, reconsider, and try a different fix.
When all tests pass, stop and give a short report: the bug, the fix, and the evidence."""

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

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- Step {step} ---")
        response = call_llm(contents, config)
        if response is None:
            print("Stopping: the LLM is unavailable.")
            return

        contents.append(response.candidates[0].content)

        if not response.function_calls:
            print("AGENT REPORT:", response.text)
            return

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
            result_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result}
                )
            )
        contents.append(types.Content(role="user", parts=result_parts))

    print("\nStopped: reached MAX_STEPS without finishing.")