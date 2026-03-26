from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from collections import defaultdict
import json
import numpy as np
import os

#Todo: check the rag_pipeline code for any errors
load_dotenv()
api_key=os.getenv("API-KEY")
embedding=HuggingFaceEmbeddings(model_name="intfloat/e5-base-v2")

youtube_db=Chroma(
    collection_name="feature_rag_youtube",
    embedding_function=embedding,
    persist_directory="./chroma_db"
)

specs_db=Chroma(
    collection_name="rag_product_specifications",
    embedding_function=embedding,
    persist_directory="./chroma_db"
)

llm=ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    api_key=api_key,
    temperature=0.2
)

def cosine_sim(a,b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def build_search_query(idea_json):
    features=[]
    idea = idea_json["idea_understanding"]
    constraints = idea_json["constraints"]

    for key,value in constraints.items():
        if key == "special_features":
            features.append("special features: " + ",".join(value))
        else:
            features.append(f"{key.replace('_', ' ')}: {str(value)}")

    query=f"""
    query: {idea['one_line_description']}
    Important features: {' '.join(features)}
    """
    return query.strip()

def retrieve_products(query,k=15):
    youtube_docs= youtube_db.similarity_search(query, k=k)
    spec_docs = specs_db.similarity_search(query, k=k)
    return youtube_docs,spec_docs

def group_by_product(youtube_docs,spec_docs):
    grouped=defaultdict(list)
    for doc in youtube_docs:
        product=doc.metadata.get("product")
        grouped[product].append(doc)

    for doc in spec_docs:
        product=doc.metadata.get("product")
        grouped[product].append(doc)

    return grouped

def build_product_profiles(grouped_docs):
    profiles={}

    for product,docs in grouped_docs.items():
        profile={
            "reviews": [], 
            "specs": {}
        }
            
        for doc in docs:
            if doc.metadata.get("type")=="review":
                profile["reviews"].append(doc.page_content)

            if doc.metadata.get("type")=="specs":
                for key, value in doc.metadata.items():
                    if key not in ["product", "source", "type"]:
                        if key not in profile["specs"]:
                            profile["specs"][key]=value
            
                # if "price_rs" in doc.metadata and profile["price"] is None:
                #     profile["price"] = str(doc.metadata["price_rs"]) + "INR"
                # else:
                #     profile["price"]=None

        profiles[product] = profile

    return profiles

def profile_to_text(profile): #error- dependent on build_product_profile 
    text = ""
    for key, value in profile["specs"].items():
        text += f"{key}: {value}. "

    text += " ".join(profile["reviews"][:3])
    return text

def score_product(profile,constraints): #Not sure
    score = 0

    # Product embedding
    product_text = profile_to_text(profile) #wip error
    product_vec = embedding.embed_query(f"passage: {product_text}")

    # Semantic feature matching
    for feature in constraints.get("special_features", []):
        feature_vec = embedding.embed_query(f"query: {feature}")
        score += cosine_sim(feature_vec, product_vec)

    # Price scoring (soft constraint)
    if "budget_price_range" in constraints:
        try:
            budget = int(''.join(filter(str.isdigit, constraints["budget_price_range"])))

            if profile["price"]:
                score += max(0, 1 - (profile["price"] / budget))
        except:
            pass

    return score

def rank_products(profiles, constraints):
    scored = []

    for product, profile in profiles.items():
        score = score_product(profile, constraints)
        scored.append((product, profile, score))

    return sorted(scored, key=lambda x: x[2], reverse=True)

def merge_rank(yt_docs, spec_docs): #ignore for now
    # give specs higher importance
    ranked = spec_docs + yt_docs
    return ranked

def save_report(input_data,response):
    json_string=response[0]['text']
    data=json.loads(json_string)

    os.makedirs("reports", exist_ok=True)

    log_data={
        "input": input_data,
        "response": data
    }

    file_path = os.path.join("reports", "market_report2.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)
    print("Report saved to:", file_path)

def generate_report(ranked_products, idea_json):
    top_products=ranked_products[:10]
    context=""

    for product, profile, score in top_products:
        context += f"""
        Product: {product}
        Specs: {profile['specs']}
        Sample Reviews: {' '.join(profile['reviews'])} 
        Score: {score}
        """

    prompt = f"""
    You are a market research analyst.

    User Idea:
    Raw Idea: {idea_json['idea_raw']}
    Idea Understanding: {idea_json['idea_understanding']}
    Constraints: {idea_json['constraints']}

    Competitor Data:
    {context}

    Generate a detailed report including:

    1. Top competing products
    2. Competitor strengths & weaknesses
    3. Market gaps
    4. Feasibility of the idea
    5. Challenges in implementation

    IMPORTANT RULES:
    - You MUST base your analysis primarily on the provided competitor data
    - You MAY use general knowledge for feasibility reasoning and challenges in implementation
    - Be analytical, not descriptive

    OUTPUT FORMAT (STRICT JSON ONLY)

    Return ONLY valid JSON. No explanation text.

    Schema:

    {{
    "top_competitors": [
        {{
        "product_name": "...",
        "price": "...",
        "key_features": ["..."],
        "strengths": ["..."],
        "weaknesses": ["..."]
        }}
    ],
    "market_gap_analysis": {{
        "existing_gaps": ["..."],
        "unmet_features": ["..."],
        "opportunity_level": "low | medium | high"
    }},
    "feasibility_analysis": {{
        "is_feasible": true/false,
        "reasoning": "...",
        "technical_challenges": ["..."],
        "cost_constraints": ["..."]
    }},
    "implementation_challenges": [
        "..."
    ]
    }}

    Ensure:
    - JSON is valid
    - No trailing commas
    - No text outside JSON
    """

    response=llm.invoke(prompt).content
    save_report(context, response)
    return response

def run_rag(idea_json):
    constraints=idea_json['constraints']
    query = build_search_query(idea_json)

    y_docs, s_docs = retrieve_products(query)

    grouped = group_by_product(y_docs, s_docs)

    profiles = build_product_profiles(grouped)

    ranked = rank_products(profiles, constraints)

    report = generate_report(ranked, idea_json)

    return report

#Driver Code
#query= "Develop a low-cost smartphone featuring a sustainable 36-hour battery life achieved via an attachable solar panel."
with open("chats/user_b60a0686_9d8c060cdc474ba491405ca464f045bc.json") as f:
    idea_json = json.load(f)
report=run_rag(idea_json)
print(report)