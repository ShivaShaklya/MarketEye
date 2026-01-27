import re
import spacy
from collections import Counter
from gemini_client_setup import call_llm
from chat_store import create_chat, save_chat, add_turn
import json

#Create json file per project per user (idea_raw,idea_understanding (domain/subdomain/stage/one-liner + target user (later, dynamically)), finalized = true/false, constraints (geolocation (place), budget (price), B2B/B2C(promotion))
#report (generated markdown/pdf), report_index (embeddings / chunks for Q&A over the report), conversation_history
#Get confirmation for domain etc., update db, continue conversation for constraints, finalize and update db, create customer persona dynamically, scrape market overview, create report
#Get customer persona and market overview from user query
#Allow cross questioning
#Ensure database + agentic competitive analysis

nlp = spacy.load("en_core_web_sm")

def calculate_confidence_score(doc):
    #Semantic focus
    noun_chunks = [chunk.root.lemma_ for chunk in doc.noun_chunks]
    if not noun_chunks:
        return 0.0
    counts = Counter(noun_chunks)
    top_ratio = counts.most_common(1)[0][1] / len(noun_chunks)
    semantic_focus_score=round(top_ratio, 2)

    #Product clarity
    product_nouns = 0
    for token in doc:
        if token.pos_=="NOUN" and token.dep_ in ["dobj", "pobj", "nsubj"]:
            product_nouns+=1
    product_clarity_score=min(product_nouns/3, 1.0)

    #Details and constraints
    constraints=0
    for token in doc:
        if token.pos_=="ADJ":
            constraints+=1
        if token.text in ["battery", "cost", "price", "power", 'speed', 'camera', 'size', 'weight']:
            constraints+=1
    constraint_score=min(constraints/4, 1.0)

    #Noise penalty
    vague_terms={"something", "thing", "stuff", "cool", "special", "nice"}
    noise=sum(1 for t in doc if t.lemma_ in vague_terms)
    noise_score=max(0.0, 1.0 - (noise * 0.25))

    scores = {
        "focus": semantic_focus_score,
        "product": product_clarity_score,
        "constraints": constraint_score,
        "noise":noise_score,
    }

    confidence = (
        scores["focus"] * 0.15 +
        scores["product"] * 0.35 +
        scores["constraints"] * 0.35 +
        scores["noise"] * 0.15
        #scores["length"] * 0.2
    )
    
    return confidence

def apply_user_edits(chat: dict, prev_understanding: dict, user_edit: str) -> dict:
    prompt_template="""You are an expert product analyst.

    You have a current structured understanding of a product idea.
    The user may confirm it or provide corrections.

    Rules:
    - If the user message clearly confirms (yes/looks good/correct): return the SAME JSON unchanged.
    - If the user message contains edits: update ONLY what the user changed.
    - Keep all keys exactly the same.
    - Return ONLY valid JSON. No markdown. No extra keys.
    """

    user_message=f"""Current JSON: {json.dumps(prev_understanding, ensure_ascii=False, indent=2)}
    User message: {user_edit}
    """
    data, updated_contents=call_llm(prompt_template,user_message,chat.get("contents", []))
    chat["contents"] = updated_contents

    required = ["domain", "subdomain", "ideation_stage", "one_line_description","justification"]
    new_understanding={k: data[k] for k in required}
    
    return new_understanding

def idea_confirmation(chat, query, confidence):
    prompt_template="""You are an expert product and startup analyst.
    Given:
    - A processed product idea: {query}
    - A confidence score indicating specificity: {confidence}

    Classify the ideation maturity of the idea using ONLY one of the following stages:
    - exploration and problem_framing (initial_stage)
    - solution_design and solution_detailing (intermediate_stage)
    - market_validation_ready (final_stage)

    Definitions:
    - exploration and problem_framing: vague idea of a product, no much details
    - solution_design and solution_detailing: a solution is proposed but not explained
    - market_validation_ready: clear solution with target users and constraints

    Then also return:
    1. Ideation stage
    2. Domain of solution
    3. Subdomain of solution
    4. One-line needs statement of the idea
    5. Short justification for choosing the ideation stage

    Return ONLY valid JSON with exactly these keys:
    {
    "domain": "...",
    "subdomain": "...",
    "ideation_stage": "...",
    "one_line_description": "...",
    "justification": "..."
    }
    No markdown. No extra keys.
    """
    user_message = f"""User query: {query}
    Confidence score (0 to 1): {confidence}
    """

    data,updated_contents=call_llm(prompt_template,user_message)
    chat["contents"] = updated_contents
    
    required = ["domain", "subdomain", "ideation_stage", "one_line_description","justification"]
    return {k: data[k] for k in required}

def preprocess_query(query):
    #Convert qury to lowercase and remove special characters
    query=query.strip().lower()
    pattern=r'[^a-z0-9\s]'
    query=re.sub(pattern,'',query)
    
    #Tokenization and lemmatization
    doc=nlp(query)
    processed_query=' '.join([tokens.lemma_ for tokens in doc if not tokens.is_stop])
    confidence_score=calculate_confidence_score(nlp(processed_query))
    print("Confidence Score:",confidence_score)
    return processed_query, confidence_score
    
def chat_orchestration(user_id, query):
    chat,chat_id=create_chat(user_id=user_id)
    chat["idea_raw"]=query
    add_turn(chat,"user",query)

    processed_query,confidence_score=preprocess_query(query)
    
    #Understanding the idea
    print("\nPRODUCT IDEA DETAILING\n")
    understanding=idea_confirmation(chat,processed_query,confidence_score)
    chat["idea_understanding"]=understanding
    chat["status"]="WAITING_IDEA_CONFIRMATION"
    add_turn(chat, "assistant", "Extracted understanding:\n" + json.dumps(understanding, ensure_ascii=False, indent=2))
    save_chat(chat)

    #Confirm/edit
    while True:
        print("I understood your idea as:\n")
        for k,v in understanding.items():
            if k!="justification":
                print(k+": "+v)
        
        user_reply= input("Is this correct? Confirm or write the changes you want to make: ")
        if user_reply.lower().strip() in {"yes","y","correct", "looks good", "ok", "okay","confirm"}:
            print("\nIdea confirmed\n")
            chat["status"]="WAITING_CONSTRAINTS"
            add_turn(chat, "assistant", "Idea confirmed. Moving to constraints.")
            save_chat(chat)
            break
        else:
            understanding=apply_user_edits(chat,understanding, user_reply)
            chat["idea_understanding"] = understanding
            add_turn(chat, "assistant", "Updated understanding:\n" + json.dumps(understanding, ensure_ascii=False, indent=2))
            save_chat(chat)

    #Constratints
    print("\nConstraint analysis\n")
    return chat_id

#
#query=input("Enter your idea: ")
query="I am building something very special. Low cost smartphones with a long battery life!!!"
#query="I am building something very cool. A low cost smartphones with a long battery life. This will be done by using a solar panel attached to the back of the phone."
#query="I am building something very cool. A smartphone in the range of Rs. 10000 with a battery life lasting 36 hours continuously. This will be done by using a solar panel attached to the back of the phone."
chat_id=chat_orchestration(user_id="user_001", query=query)