import os
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url).json()

valid_models = []
for model in response.get("models", []):
    methods = model.get("supportedGenerationMethods", [])
    if "generateContent" in methods:
        valid_models.append(model["name"])

print("Valid models:", valid_models)
