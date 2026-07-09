import os
import sys
from dotenv import load_dotenv

# Ensure we use the exact provider setup
from backend.ai.llm.gemini_provider import GeminiLLMProvider

def main():
    print("--- Gemini Diagnostic ---")
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        print(f"Gemini key loaded: yes")
        print(f"Gemini key length: {len(key)}")
        print(f"Gemini key suffix: ...{key[-4:]}")
    else:
        print("Gemini key loaded: no")
        sys.exit(1)

    try:
        provider = GeminiLLMProvider()
        print(f"Gemini model: {provider.model_name}")
        
        print("\nSending diagnostic request: 'Reply with exactly OK'")
        response = provider.generate_response("Reply with exactly OK")
        print("SUCCESS! Response received:")
        print(f"[{response.strip()}]")
    except Exception as e:
        print("\nFAILED! Exception raised:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
