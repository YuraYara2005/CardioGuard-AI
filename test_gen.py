import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

for model in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=headers).json()
    if 'error' in response:
        print(f"{model} Failed:", response['error']['message'])
    else:
        print(f"{model} Succeeded")
