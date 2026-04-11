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
from rag_pipeline1 import (
    retrieve_products,
    group_by_product,
    build_product_profiles,
    rank_products
)

#NDCG@k curve
#Plot 4 similarity score graphs
#Generative evaluation: Faithfulness, Relevance

load_dotenv()
key=os.getenv("API-KEY")
embedding=HuggingFaceEmbeddings(model_name="intfloat/e5-base-v2")
client = genai.Client(api_key=key)

OUTPUT_FILE="evaluation_results_retrieve1.json"
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

def extract_product_name(text, source):
    if source == "specs":
        match = re.search(r"([A-Za-z0-9\s\-]+?)\s+is\s+a", text)
        if match:
            return match.group(1).strip()
    else:
        match = re.search(r"Product:\s*(.+)", text)
        if match:
            return match.group(1).strip()
    return None

def normalize_product(name):
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name

def detect_category(idea_json):
    text = idea_json["idea_understanding"]["one_line_description"].lower()

    if re.search(r"\b\w*\s*(laptop|notebook|ultrabook)s?\b", text):
        return "laptops"
    elif re.search(r"\b\w*\s*(smartphone|phone|mobile)s?\b", text):
        return "smartphones"

    return "general"

def precision_at_k_products(ranked, gt_products, k):
    ranked_k = ranked[:k]
    gt_set = set(gt_products.keys())

    hits = sum(1 for p in ranked_k if p in gt_set)
    return hits / k

def recall_at_k_products(ranked, gt_products, k):
    ranked_k = ranked[:k]
    gt_set = set(gt_products.keys())

    hits = len(set(ranked_k) & gt_set)
    #hits = sum(1 for p in ranked_k if p in gt_set)
    return hits / len(gt_set) if gt_set else 0

def ndcg_at_k_products(ranked, gt_products, k):
    ranked_k = ranked[:k]

    #Calculatong DCG
    dcg = 0
    for i, product in enumerate(ranked_k):
        rel = gt_products.get(product, 0)
        dcg += (2**rel - 1) / math.log2(i + 2)

    #Calculating IDCG
    ideal = sorted(gt_products.values(), reverse=True)[:k]
    idcg = 0
    for i, rel in enumerate(ideal):
        idcg += (2**rel - 1) / math.log2(i + 2)

    ndcg=dcg / idcg
    if ndcg>idcg:
        print("Error: DCG exceeds IDCG")
        print(gt_products)

    return  ndcg

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
    
    abc=" ".join(parts)
    return abc

def gt_to_products(ground_truth):
    product_scores={}

    for gt in ground_truth:
        doc_id=gt['doc_id']
        rel=gt['relevance']

        product=extract_product_name(gt['text'], gt['source'])

        if not product:
            print("No product name found in:", gt['text'])
            continue
        else:
            #print("Extracted product:", product)
            product=normalize_product(product)

        if product not in product_scores:
            product_scores[product]=rel

        product_scores[product] = max(product_scores[product], rel)
    return product_scores

def retrieve_ranked_products(query, category, constraints):
    a_docs, y_docs, s_docs = retrieve_products(query, category)
    print(len(a_docs), len(y_docs), len(s_docs))
    grouped = group_by_product(a_docs, y_docs, s_docs)
    print("Grouped into products:", len(grouped))
    profiles = build_product_profiles(grouped)
    print("Built product profiles:", len(profiles))
    ranked = rank_products(profiles, constraints)
    if not ranked:
        print("No products retrieved for query:", query)
        exit(1)
    return ranked

def evaluate_metrics_actual_pipeline(idea_json, ground_truth):
    query = idea_to_query(idea_json)
    category = detect_category(idea_json)
    constraints = idea_json["constraints"]

    # 🔥 Use ACTUAL pipeline
    ranked = retrieve_ranked_products(query, category, constraints)

    ranked_products = list(dict.fromkeys(normalize_product(product) for product, _, _ in ranked))

    # Convert GT → product level
    gt_products = gt_to_products(ground_truth)
    print("\nGT Products:", set(gt_products.keys()))
    print("Ranked Products:", set(ranked_products[:10]))

    precision = precision_at_k_products(ranked_products, gt_products, 10)
    recall = recall_at_k_products(ranked_products, gt_products, 10)
    ndcg = ndcg_at_k_products(ranked_products, gt_products, 10)

    result = {
        "precision@10": round(precision, 3),
        "recall@10": round(recall, 3),
        "ndcg@10": round(ndcg, 3)
    }

    print(result)
    return result

def calc_average_metrics(metrics_json):
    total_p, total_r, total_n = 0, 0, 0
    for i in metrics_json['results']:
        p,r,n=i['precision@10'],i['recall@10'],i['ndcg@10']
        total_p+=p
        total_r+=r
        total_n+=n
    avg_p=total_p/10
    avg_r=total_r/10
    avg_n=total_n/10
    print(f"\nAverage Precision@10: {avg_p:.3f}")
    print(f"Average Recall@10: {avg_r:.3f}")
    print(f"Average NDCG@10: {avg_n:.3f}")

def save_results(results):
    output = {
        "timestamp": str(datetime.now()),
        "results": results
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved results to {OUTPUT_FILE}")

#Driver Code
if __name__ == "__main__":
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
    all_results=[]
    for idea in ideas:
        print("Processing:",idea)
        idea_json=json.load(open(idea,encoding="utf-8"))
        ground_truth_json=json.load(open(ideas_dict[idea],encoding="utf-8"))
        results = evaluate_metrics_actual_pipeline(idea_json, ground_truth_json)
        all_results.append(results)
    save_results(all_results)

    #calc_average_metrics(json.load(open(".\evaluation_results_retrieve1.json", encoding="utf-8")))

