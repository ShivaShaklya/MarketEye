from google import genai
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
api_key = os.getenv("API-KEY")

# Initialize client
client = genai.Client(api_key=api_key)

try:
    # Simple test prompt
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents="Reply with exactly: OK",
        config={"response_mime_type": "text/plain"}
    )

    # Extract response safely
    text = response.candidates[0].content.parts[0].text.strip()

    print("✅ LLM is working!")
    print("Response:", text)

except Exception as e:
    print("❌ LLM call failed")
    print("Error:", e)



