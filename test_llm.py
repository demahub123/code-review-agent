import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
        http_options=types.HttpOptions(timeout=60000),
)
MODEL = "gemini-3.5-flash-lite"

response = client.models.generate_content(
    model=MODEL,
    contents="In one sentence, what does a Python function average([2, 4, 6]) that returns 3.0 instead of 4 probably have wrong?",
)
print(response.text)