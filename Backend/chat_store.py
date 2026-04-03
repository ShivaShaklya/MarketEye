import os, json, uuid
from datetime import datetime
from typing import List, Dict, Any

CHATS_DB="chats"
os.makedirs(CHATS_DB,exist_ok=True)

def new_chat_id():
    return uuid.uuid4().hex

def now_iso():
    return datetime.utcnow().isoformat()+"Z"

def chat_path(chat_id: str) -> str:
    return os.path.join(CHATS_DB, f"{chat_id}.json")

def create_chat(user_id: str) -> Dict[str,Any]:
    now=now_iso()
    chat_id=new_chat_id()
    init_json_content={
        "chat_id": chat_id,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,

        "status": "WAITING_IDEA", #WAITING_IDEA_CONFIRMATION | WAITING_CONSTRAINTS | WAITING_CONSTRAINTS_CONFIRMATION | CONFIRMED
        "finalized": False,

        #memory_history
        "contents": [],

        #App state
        "idea_raw": "",
        "idea_understanding":{},
        "constraints":{},
        "competitive_analysis": None,

        #Log
        "conversation_history": []
    }
    return init_json_content, chat_id

def save_chat(chat: Dict[str, Any]) -> None:
    chat["contents"] = trim_contents(chat.get("contents", []), max_messages=15)

    chat["updated_at"]=now_iso()
    path=chat_path(chat["user_id"]+"_"+chat["chat_id"])
    tmp=path+".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(chat, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def load_chat(chat_id: str) -> Dict[str, Any]:
    with open(chat_path(chat_id), "r", encoding="utf-8") as f:
        return json.load(f)

def add_turn(chat: Dict[str, Any], role: str, text: str) -> None:
    chat["conversation_history"].append({
        "ts": now_iso(),
        "role": role,
        "text": text
    })

def trim_contents(contents: List[Dict[str, Any]], max_messages: int = 15) -> List[Dict[str, Any]]:
    if max_messages <= 0:
        return []
    return contents[-max_messages:] if len(contents) > max_messages else contents
