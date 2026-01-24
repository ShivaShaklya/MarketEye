from google import genai
from dotenv import load_dotenv
import os
import json
from typing import Dict, Any

load_dotenv()
api_key1=os.getenv("API-KEY")
client=genai.Client(api_key=api_key1)

'''#
response=client.models.generate_content_stream(
    model="gemini-flash-latest",
    contents="why do the stars twinkle?"
)

for stream in response:
    print(stream.text)

#
chat=client.chats.create(model="gemini-flash-lite-latest")

while True:
    message=input("> ")
    if message=="exit":
        break
    result=chat.send_message(message)
    print(result.text)'''
#
def call_llm(prompt_template: str, user_message= str):
    response=client.models.generate_content(
        model="gemini-flash-latest",
        contents=user_message,
        config={
            "system_instruction": prompt_template,
            "response_mime_type":"application/json"
        },
    )

    text=(response.text or "").strip()
    try:
        data=json.loads(text)
        return data
    except:
        raise ValueError("Incorrect output format by LLM. Raw output:\n",text)
    