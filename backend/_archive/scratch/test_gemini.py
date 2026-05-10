import os
from google import genai
from google.genai import types

api_key = "AIzaSyCWP7ogYrEiJZUbCAVpDpBh8tmI-nqSoF0"
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Merhaba, bir test mesajı."
    )
    print(f"Success: {response.text}")
except Exception as e:
    print(f"Error: {e}")
