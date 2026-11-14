import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from agent.tools import read_file, run_tests, apply_patch

load_dotenv()
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=60000),
)
MODEL = "gemini-3.5-flash-lite"

config = types.GenerateContentConfig(
    tools=[read_file, run_tests, apply_patch],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)

response = client.models.generate_content(
    model=MODEL,
    contents="The project in the folder 'sample_project' may have bugs. Find out whether its tests pass.",
    config=config,
)

if response.function_calls:
    for call in response.function_calls:
        print("TOOL CHOSEN:", call.name)
        print("ARGUMENTS:", call.args)
else:
    print("No tool chosen:", response.text)