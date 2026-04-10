from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from collections import defaultdict
import json
import numpy as np
import re
import os

SOURCE_WEIGHTS={
    "amazon": 0.4,
    "youtube": 0.35,
    "specs": 0.25
}

load_dotenv()
api_key=os.getenv("API-KEY")
embedding=HuggingFaceEmbeddings(model_name="intfloat/e5-base-v2")

amazon_db=Chroma(
    collection_name="feature_rag_amazon",
    embedding_function=embedding,
    persist_directory="../chroma_db"
)

youtube_db=Chroma(
    collection_name="feature_rag_youtube",
    embedding_function=embedding,
    persist_directory="../chroma_db"
)

specs_db=Chroma(
    collection_name="rag_product_specifications",
    embedding_function=embedding,
    persist_directory="../chroma_db"
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

def retrieve_products(query, category, k=15):
    try:
        amazon_docs = amazon_db.similarity_search(query, k=k, filter={"category": category})
    except:
        amazon_docs = []

    try:
        youtube_docs= youtube_db.similarity_search(query, k=k, filter={"category": category})
    except:
        youtube_docs = []

    try:
        spec_docs = specs_db.similarity_search(query, k=k, filter={"category": category})
    except:
        spec_docs = []

    #Fallback
    if not amazon_docs and not youtube_docs:
        amazon_docs = amazon_db.similarity_search(query, k=k)
        youtube_docs = youtube_db.similarity_search(query, k=k)
    
    if not spec_docs:
        spec_docs = specs_db.similarity_search(query, k=k)

    return amazon_docs,youtube_docs,spec_docs

def group_by_product(amazon_docs,youtube_docs,spec_docs):
    grouped=defaultdict(list)
    for doc in amazon_docs:
        product=doc.metadata.get("product")
        grouped[product].append(doc)

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
            "specs": {},
            "sources":[]
        }
            
        for doc in docs:
            src=doc.metadata.get("source")
            profile["sources"].append(src)

            if doc.metadata.get("type")=="review":
                #profile["reviews"].append(doc.page_content)
                profile["reviews"].append({"text": doc.page_content,"source": src})

            if doc.metadata.get("type")=="specs":
                for key, value in doc.metadata.items():
                    if key not in ["product", "source", "type"]:
                        if key not in profile["specs"]:
                            profile["specs"][key]=value

        profiles[product] = profile

    return profiles

def profile_to_text(profile):
    text = ""
    for key, value in profile["specs"].items():
        text += f"{key}: {value}. "

    #text += " ".join(profile["reviews"][:3])
    for review in profile["reviews"][:3]:
        text += f"Review from {review['source']}: {review['text']} "
    return text

def score_product(profile,constraints): #Not sure ##Understand
    score = 0

    # Product embedding
    product_text = profile_to_text(profile)
    product_vec = embedding.embed_query(f"passage: {product_text}")

    # Semantic feature matching
    for feature in constraints.get("special_features", []):
        feature_vec = embedding.embed_query(f"query: {feature}")
        score += 0.1*cosine_sim(feature_vec, product_vec)

        for review in profile.get("reviews", []):
            text=review.get("text", "")
            source=review.get("source", "")
            weight=SOURCE_WEIGHTS.get(source, 0.1)
            review_vec = embedding.embed_query(f"passage: {text}")
            score+= weight * cosine_sim(feature_vec, review_vec)

        if profile.get("specs"):
            spec_text = " ".join([f"{k}: {v}" for k, v in profile["specs"].items()])
            spec_vec = embedding.embed_query(f"passage: {spec_text}")

            score += SOURCE_WEIGHTS["specs"] * cosine_sim(feature_vec, spec_vec)

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

def detect_category(idea_json):
    text = idea_json["idea_understanding"]["one_line_description"].lower()

    if re.search(r"\blaptops?\b|\bnotebook\b", text):
        return "laptops"
    elif re.search(r"\bsmartphones?\b|\bphones?\b|\bmobiles?\b", text):
        return "smartphones"

    return "general"

def save_report(input_data,response):
    print("\nSave Report called\n")
    json_string=response[0]['text']
    data=json.loads(json_string)
    #input1=json.loads(input_data)

    os.makedirs("reports", exist_ok=True)

    log_data={
        "input": input_data,
        "response": data
    }

    file_path = os.path.join("reports", "market_report10.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)
    print("Report saved to:", file_path)

def generate_report(ranked_products, idea_json):
    top_products=ranked_products[:10]
    context=""
    context_json={}
    reviews_json={}
    reviews_text=""
    ctr1=0

    for product, profile, score in top_products:
        for review in profile.get("reviews", []):
            text=review.get("text", "")
            source=review.get("source", "")
            #reviews_text+= f"Review from {source}: {text}\n"
            reviews_text+=f"text. "
            ctr1+=1
            reviews_json[ctr1]={"src:": source, "text": text}

        context += f"""
        Product: {product}
        Specs: {profile['specs']}
        Sample Reviews: {reviews_text} 
        Relevance Score: {score}
        """
        context_json[product]={
            "specs": profile["specs"],
            "reviews": reviews_json,
            "score": score
        }
        reviews_text="" #reset for next product
        reviews_json={} #reset for next product

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
    - Develop a scoring metric based on competiveness for each competitor and return it

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
        "weaknesses": ["..."],
        "competitive score":
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
    save_report(context_json, response)
    return response

def run_rag(idea_json):
    constraints=idea_json['constraints']
    
    category=detect_category(idea_json)
    query = build_search_query(idea_json)

    a_docs, y_docs, s_docs = retrieve_products(query, category)

    grouped = group_by_product(a_docs, y_docs, s_docs)

    profiles = build_product_profiles(grouped)

    ranked = rank_products(profiles, constraints)

    report = generate_report(ranked, idea_json)

    return report

def generate_report_for_eval(ranked_products, idea_json):
    top_products = ranked_products[:10]
    context = ""
    context_json = {}
    reviews_json = {}
    reviews_text = ""
    ctr1 = 0
    

    for product, profile, score in top_products:
        for review in profile.get("reviews", []):
            text = review.get("text", "")
            source = review.get("source", "")
            reviews_text += f"{text} "
            ctr1 += 1
            reviews_json[ctr1] = {"src": source, "text": text}

        context += f"""
        Product: {product}
        Specs: {profile['specs']}
        Sample Reviews: {reviews_text}
        Relevance Score: {score}
        """

        context_json[product] = {
            "specs": profile["specs"],
            "reviews": reviews_json,
            "score": score
        }

        reviews_text = ""
        reviews_json = {}

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
    - Develop a scoring metric based on competiveness for each competitor and return it

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
        "weaknesses": ["..."],
        "competitive score":
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

    response = llm.invoke(prompt)
    
    raw = response.content if hasattr(response, "content") else response
    
    # Handle Gemini structured output
    if isinstance(raw, list):
        try:
            output = raw[0]["text"]
        except:
            output = str(raw)

    elif isinstance(raw, dict):
        output = raw.get("text", str(raw))
    else:
        output = str(raw)

    return output, context_json

#Driver Code
if __name__=="__main__":
    query= "Develop a low-cost smartphone featuring a sustainable 36-hour battery life achieved via an attachable solar panel."
    with open("chats/user_b60a0686_9d8c060cdc474ba491405ca464f045bc.json") as f:
        idea_json = json.load(f)
    report=run_rag(idea_json)
    print(report)