import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from agent import tools, memory

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
MAX_STEPS = 20
USE_MEMORY = True
MIN_GAP = 5.0  # seconds between LLM calls: the free tier allows 15 per minute

BASE_TOOLS = {
    "read_file": tools.read_file,
    "run_tests": tools.run_tests,
    "apply_patch": tools.apply_patch,
}

client = genai.Client(http_options=types.HttpOptions(timeout=60000))
_last_call = 0.0


def build_prompt(use_memory):
    steps = ["Run the tests to see what fails."]
    if use_memory:
        steps.append(
            "Call search_memory with the error types and symptoms you see (for example "
            "'IndexError off by one', 'float rounding', 'ordering lost'), not function names, "
            "to find lessons from past cases. Treat the results as hints, not facts."
        )
    steps += [
        "Read the relevant source file to find the cause. Never edit test files.",
        "Fix the bugs with patches (apply_patch), using file paths exactly as they appear "
        "inside the project folder (for example sample_project2/utils.py).",
        "Run the tests again to verify the fix.",
        "If a patch fails or tests still fail, read the error, reconsider, and try a different fix.",
    ]
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return (
        "You are a code review and bug triage agent for Python projects.\n"
        "Work step by step using your tools:\n"
        f"{numbered}\n"
        "When all tests pass, stop and give a short report: the bugs, the fixes, and the evidence."
    )


def call_llm(contents, config, retries=4):
    """Call the LLM, staying under the free-tier rate limit and waiting out 429 errors."""
    global _last_call
    for attempt in range(retries + 1):
        wait = MIN_GAP - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            return client.models.generate_content(
                model=MODEL, contents=contents, config=config
            )
        except Exception as e:
            print(f"  LLM error (attempt {attempt + 1}): {str(e)[:200]}")
            time.sleep(65 if "429" in str(e) else 5)
    return None


def extract_lessons(report, failure_text):
    """Ask the LLM to turn a finished run into short, general lessons."""
    prompt = (
        "Below are the first test failures and the final report of a bug-fixing run.\n"
        "Write 1 to 3 short, general lessons, one per line, each exactly in the form:\n"
        "symptom: ... | cause: ... | fix: ...\n"
        "Do not mention project, file or function names. Plain text only, no bullets.\n\n"
        f"TEST FAILURES:\n{failure_text[:600]}\n\nREPORT:\n{report[:1200]}"
    )
    response = call_llm(prompt, types.GenerateContentConfig(), retries=1)
    if response is None or not response.text:
        return []
    lines = [l.strip() for l in response.text.splitlines() if "symptom" in l.lower()]
    return lines[:3]


def run_agent(goal):
    tool_map = dict(BASE_TOOLS)
    if USE_MEMORY:
        tool_map["search_memory"] = memory.search_memory

    config = types.GenerateContentConfig(
        system_instruction=build_prompt(USE_MEMORY),
        tools=list(tool_map.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=goal)])]

    first_failure = ""
    last_tests = ""
    patches = 0
    tool_errors = 0

    def result_dict(success, steps, llm_error=False):
        return {
            "success": success,
            "steps": steps,
            "patches": patches,
            "tool_errors": tool_errors,
            "llm_error": llm_error,
        }

    def finish(report, steps):
        success = "passed" in last_tests and "failed" not in last_tests
        if USE_MEMORY:
            lessons = extract_lessons(report, first_failure) if success else []
            memory.save_episode({
                "project": tools._sandbox.name,
                "failure_text": first_failure[:600],
                "report": report[:800],
                "lessons": lessons,
                "success": success,
                "steps": steps,
                "patches": patches,
            })
            print(f"\nSaved to memory: success={success}, steps={steps}, patches={patches}")
            for lesson in lessons:
                print("LESSON:", lesson)
        else:
            print(f"\nFinished (memory off): success={success}, steps={steps}, patches={patches}")
        return result_dict(success, steps)

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- Step {step} ---")
        response = call_llm(contents, config)
        if response is None:
            print("Stopping: the LLM is unavailable.")
            return result_dict(False, step, llm_error=True)

        contents.append(response.candidates[0].content)

        if not response.function_calls:
            print("AGENT REPORT:", response.text)
            return finish(response.text or "", step)

        result_parts = []
        for call in response.function_calls:
            args = dict(call.args)
            print(f"ACT: {call.name}({args})")
            func = tool_map.get(call.name)
            try:
                result = func(**args) if func else f"ERROR: unknown tool {call.name}"
            except Exception as e:
                result = f"ERROR: tool crashed: {e}"
            print("RESULT:", result[:300])

            if result.startswith("ERROR"):
                tool_errors += 1
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