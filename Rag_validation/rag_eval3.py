import json
import math
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from google import genai
import re

#Generation Component Evaluation
    #Faithfulness, Answer Relevancy

load_dotenv()
key=os.getenv("API-KEY")
embedding=HuggingFaceEmbeddings(model_name="intfloat/e5-base-v2")
client = genai.Client(api_key=key)

OUTPUT_FILE="evaluation_results_retrieve.json"
K_POOL=10
K_RETRIEVE = 15

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

def save_results(results):
    output = {
        "timestamp": str(datetime.now()),
        "results": results
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved results to {OUTPUT_FILE}")

def precision_at_k(retrieved, ground_truth, k):
    retrieved_k = [d["doc_id"] for d in retrieved[:k]]
    gt_ids = set(d["doc_id"] for d in ground_truth)

    return sum(d in gt_ids for d in retrieved_k) / k


def recall_at_k(retrieved, ground_truth, k):
    retrieved_k = [d["doc_id"] for d in retrieved[:k]]
    gt_ids = set(d["doc_id"] for d in ground_truth)

    return sum(d in gt_ids for d in retrieved_k) / len(gt_ids) if gt_ids else 0


def dcg(retrieved, ground_truth, k):
    rel_map = {d["doc_id"]: d["relevance"] for d in ground_truth}

    score = 0
    for i, doc in enumerate(retrieved[:k]):
        rel = rel_map.get(doc["doc_id"], 0)
        score += (2**rel - 1) / math.log2(i + 2)

    return score

def ndcg_at_k(retrieved, ground_truth, k):
    ideal = sorted(ground_truth, key=lambda x: x["relevance"], reverse=True)

    ideal_dcg = dcg(ideal, ground_truth, k)
    actual_dcg = dcg(retrieved, ground_truth, k)

    return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0

def detect_category(idea_json):
    text = idea_json["idea_understanding"]["one_line_description"].lower()

    if re.search(r"\b\w*\s*(laptop|notebook|ultrabook)s?\b", text):
        return "laptops"
    elif re.search(r"\b\w*\s*(smartphone|phone|mobile)s?\b", text):
        return "smartphones"

    return "general"
    
def idea_to_query(idea_json):
    constraints=idea_json.get("constraints",{})
    idea=idea_json.get("idea_raw", "")
    parts=[]
    parts.append(idea_json['idea_understanding']['one_line_description'])

    if constraints.get("special_features"):
        features = constraints["special_features"]
        if isinstance(features, list):
            parts.extend(features)
        elif isinstance(features, str):
            parts.append(features)

    if constraints.get("feature_priority"):
        parts.append(constraints["feature_priority"])

    if constraints.get("budget_price_range"):
        parts.append(constraints["budget_price_range"])
    
    return " ".join(parts)

def evaluate_metrics(query, category, db_dict, ground_truth):
    # Step 3: Retrieve (main system)
    retrieved = retrieve_docs(query, category, db_dict, k=K_RETRIEVE)

    # Step 4: Metrics
    precision = precision_at_k(retrieved, ground_truth, K_RETRIEVE)
    recall = recall_at_k(retrieved, ground_truth, K_RETRIEVE)
    ndcg = ndcg_at_k(retrieved, ground_truth, K_RETRIEVE)

    result = {
        "query": query,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "ndcg": round(ndcg, 3),
        "num_ground_truth": len(ground_truth)
    }

    print(result)

    return result

def llm_call(query, doc_text, client):
    prompt = f"""
    Query: {query}

    Document:
    {doc_text}

    Rate relevance:
    3 = highly relevant
    2 = relevant
    1 = slightly relevant
    0 = not relevant

    Return only the number.
    """
    
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config={"response_mime_type": "text/plain"}
    )
    print(response)
    result=response.candidates[0].content.parts[0].text

    match = re.search(r"[0-3]", result)
    if match:
        score = int(match.group())
    else:
        print("no match")
        score = 0
    score=max(0, min(score, 3))
    return score

def retrieve_docs(query, category, db_dict, k=15):
    print("SIMILARITY SEARCH")
    formatted_query= f"query: {query}"
    #query_vec = embedding.embed_query(formatted_query)
    all_docs=[]
    #Add filter
    for source, db in db_dict.items():
        if category!="general":
            results = db.similarity_search_with_score(
                    formatted_query,
                    k=k,
                    filter={"category": category}
                )
            print(f"{source} docs with filter:", len(results))
        
        else:
            results = db.similarity_search_with_score(formatted_query, k=k)
            print(f"{source} docs without filter:", len(results))
        
        for doc, score in results:
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.page_content[:1500]))

            all_docs.append({
                "doc_id": doc_id,
                "text": doc.page_content,
                "source": source,
                "similarity_score": score
            })

    all_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
    return all_docs

def save_ground_truth(query, pool, ground_truth, folder="ground_truth"):
    os.makedirs(folder, exist_ok=True)

    gt_ids = {d["doc_id"]: d["relevance"] for d in ground_truth}

    saved_docs = []

    for doc in pool:
        if doc["doc_id"] in gt_ids:
            saved_docs.append({
                "doc_id": doc["doc_id"],
                "relevance": gt_ids[doc["doc_id"]],
                "source": doc["source"],
                "text": doc["text"]
            })

    # filename based on query
    file_name = query.replace(" ", "_").replace("/", "")[:100] + ".json"
    file_path = os.path.join(folder, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(saved_docs, f, indent=2, ensure_ascii=False)

    print(f"Saved GT docs → {file_path}")

def build_ground_truth(query, pool, client):
    print("Building ground truth (single LLM call)...")

    docs_text = []
    for doc in pool:
        docs_text.append(f"""
        DOC_ID: {doc['doc_id']}
        CONTENT: {doc['text'][:500]}
        """)

    docs_block = "\n".join(docs_text)

    prompt = f"""
    You are evaluating document relevance.

    Query:
    {query}

    For EACH document assign:
    3 = highly relevant
    2 = relevant
    1 = slightly relevant
    0 = not relevant

    Return STRICT JSON:
    [
      {{"doc_id": "...", "score": 0}}
    ]

    Rules:
    - Include ALL DOC_IDs
    - Do NOT skip any
    - Do NOT add extra text

    Documents:
    {docs_block}
    """

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )

        result = response.candidates[0].content.parts[0].text.strip()
        print("LLM RAW:", result[:500])

        try:
            parsed = json.loads(result)
        except:
            match = re.search(r"\[.*\]", result, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                print("Failed to parse LLM output as JSON.")
                return "Error"

    except Exception as e:
        print("[LLM ERROR]:", e)

    ground_truth = []
    scored_docs = []

    for item in parsed:
        doc_id = item.get("doc_id")
        score = int(item.get("score", 0))

        if not doc_id:
            continue

        scored_docs.append({"doc_id": doc_id, "relevance": score})

        if score > 0:
            ground_truth.append({"doc_id": doc_id, "relevance": score})

    if not ground_truth and scored_docs:
        print("Fallback triggered")
        scored_docs.sort(key=lambda x: x["relevance"], reverse=True)
        ground_truth = scored_docs[:5]

    save_ground_truth(query, pool, ground_truth)

    return ground_truth

def build_pool(query,category, db_dict):
    print("Building pool...")
    pool=[]
    r=retrieve_docs(query, category, db_dict, k=K_POOL)
    if not r:
        raise ValueError(f"No documents retrieved for query: {query}")
    
    pool.extend(r)
    print("Build pool:", len(pool))
    
    seen = set()
    unique_pool = []
    for d in pool:
        if d["doc_id"] not in seen:
            seen.add(d["doc_id"])
            unique_pool.append(d)

    return unique_pool

def evaluate(idea_json, db_dict, client, ground_truth=None):
    query = idea_to_query(idea_json)
    print(f"\nEvaluating Query: {query}")
    category=detect_category(idea_json)
    print("category:", category)

    # # Step 1: Build pool
    # pool = build_pool(query,category, db_dict)

    # # Step 2: Ground truth
    # ground_truth = build_ground_truth(query, pool, client)

    eval_score=evaluate_metrics(query, category, db_dict, ground_truth)
    return eval_score
    

#Driver Code
db_dict={
    "youtube": youtube_db,
    "amazon": amazon_db,
    "specs": specs_db
}
ideas=[]
ideas_dict={}
for ctr in range(1,11):
    idea_file= f"./Ideas/idea{ctr}.json"
    ground_truth_file=f"./ground_truth/idea{ctr}.json"
    ideas_dict[idea_file]=ground_truth_file
    ideas.append(idea_file)

#ideas=['..\Ideas\idea2.json']
idea_data=[]
for idea in ideas:
    print("Processing:",idea)
    idea_json=json.load(open(idea))
    ground_truth_json=json.load(open(ideas_dict[idea]))
    results = evaluate(idea_json, db_dict, client,ground_truth_json)
    save_results(results)