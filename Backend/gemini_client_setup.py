from google import genai
from dotenv import load_dotenv
import os
import json
from typing import List, Dict, Any, Optional, Tuple

load_dotenv()
api_key1=os.getenv("API-KEY")
client=genai.Client(api_key=api_key1)

#
def call_llm(prompt_template: str, user_message: str, history_contents: Optional[List[Dict[str,Any]]]=None) -> Tuple[Dict[str,Any], List[Dict[str,Any]]]:

    contents: List[Dict[str,Any]]=[]
    if history_contents:
        contents.extend(history_contents)

    contents.append({"role":"user","parts":[{"text":user_message}]})

    response=client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=contents,
        config={
            "system_instruction": prompt_template,
            "response_mime_type":"application/json"
        },
    )

    text=(response.text or "").strip()
    try:
        data=json.loads(text)
        contents.append({"role":"model","parts":[{"text":text}]})
        return data,contents
    except:
        raise ValueError("Incorrect output format by LLM. Raw output:\n",text)
    