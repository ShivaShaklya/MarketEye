from gemini_client_setup import call_llm
from chat_store import add_turn, save_chat
import json

def create_persona(chat):
    prompt = """
    You are a market research expert specialized in startups and small businesses.

    Based on the given idea and constraints, create a realistic primary customer persona.

    Rules:
    - Personas must align with constraints.
    - Use own market knowledge to inform persona creation.
    - Keep the persona realistic and not aspirational

    Return ONLY valid JSON with this structure:
    {
    "personas": [
        {
        "name": "...",
        "demographic_details": ["...", "..."]
        "role_or_profile": "...",
        "primary_need": "...",
        "key_pain_points": ["...", "..."],
        "buying_motivation": "...",
        "constraints_sensitivity": {
            "price": "...",
            "feature": ["...","..."]
        }
        "adoption_friction": ["...","..."]
        }
    ]
    }
    """

    context = f"""Idea Understanding: {chat['idea_understanding']}\nConstraints: {chat['constraints']}"""

    data, updated_contents = call_llm(
        prompt_template=prompt,
        user_message=context,
        history_contents=chat.get("contents", [])
    )

    chat["contents"] = updated_contents
    chat["customer_persona"] = data
    return data

def create_market_overview(chat):
    prompt = """
    You are a market research analyst specialized in startups and small businesses.

    Provide a high-level market overview for the idea described.

    Rules:
    - Stay aligned to constraints (geography, price sensitivity, users).
    - No fake statistics or made-up numbers.
    - Focus on structure, trends, and dynamics.
    - Return sources of information

    Return ONLY valid JSON with this structure:
    {
    "market_definition": "...",
    "target_market_characteristics": [
        "...",
        "..."
    ],
    "key_trends": [
        "...",
        "..."
    ],
    "demand_drivers": [
        "...",
        "..."
    ],
    "major_risks": [
        "...",
        "..."
    ]
    }
    """

    context = f"""Idea Understanding: {chat['idea_understanding']}\nConstraints: {chat['constraints']}"""

    data, updated_contents = call_llm(
        prompt_template=prompt,
        user_message=context,
        history_contents=chat.get("contents", [])
    )

    chat["contents"] = updated_contents
    chat["market_overview"] = data
    return data

def create_report1(chat):
    add_turn(chat, "assistant", "Generating customer personas")
    persona=create_persona(chat)
    add_turn(chat, "assistant", json.dumps(persona, indent=2))

    add_turn(chat, "assistant", "Analyzing market overview")
    market=create_market_overview(chat)
    add_turn(chat, "assistant", json.dumps(market, indent=2))

    chat["status"] = "MARKET_RESEARCH_READY"
    chat["finalized"]= True
    save_chat(chat)
    
    #Print report
    print("\n\nREPORT 1\n\n")
    idea_understanding=chat["idea_understanding"]
    constraints=chat["constraints"]
    
    print("PRODUCT IDEA")
    for k,v in idea_understanding.items():
        print(f"{k}: {v}")
    print()
    print("CONSTRAINTS")
    for k,v in constraints.items():
        print(f"{k}: {v}")
    print()
    print("CUSTOMER PERSONA")
    for k,v in persona.items():
        print(f"{k}: {v}")
    print()
    print("MARKET OVERVIEW")
    for k,v in market.items():
        print(f"{k}: {v}")
    print()

