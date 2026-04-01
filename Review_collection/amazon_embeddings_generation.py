import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

'''##Specs matching
def match_spec(feature, normalized_specs):
    words=feature.lower().split()
    matches=[]
    for spec_key, value in normalized_specs.items():
        if any(word in spec_key for word in words):
            matches.append(f"{spec_key}: {value}")
    return matches if matches else None

def normalize_specs(data):
    specs = data
    return {k.lower().replace("_", " "): v for k, v in specs.items()}

#Driver Code
INPUT_DIR = r".\data\laptops_insights_finalized"
OUTPUT_DIR = "./data/processed_amazon/laptops"
ctr=0
os.makedirs(OUTPUT_DIR, exist_ok=True)

for file in os.listdir(INPUT_DIR):
    if not file.endswith(".json"):
        continue

    file_path = os.path.join(INPUT_DIR, file)
    with open(file_path, "r", encoding="utf-8") as f:
        print("Processing:", file)
        feature_data = json.load(f)

    #Get reviews and product specifications
    product = file.removesuffix("_insights.json").replace("_", " ").title()

    #Specs mapping
    fname=str(file.removesuffix("_insights.json"))
    with open(f"./data/product_specifications/laptops/{fname}.json","r", encoding="utf-8") as f1:
        specs_data=json.load(f1)
    
    normalized_specs=normalize_specs(specs_data)
    feature_records=[]

    for item in feature_data["features"]:
        feature=item["feature"].lower()
        sentiment=item["sentiment"]
        positive_mentions=item.get("positive_mentions",0)
        negative_mentions=item.get("negative_mentions",0)
        neutral_mentions=item.get("neutral_mentions",0)
        total_mentions=item.get("total_mentions",0)
        feature_score=item.get("feature_score",0)
        
        spec_value=match_spec(feature,normalized_specs)
        record = {
            "feature": feature,
            "sentiment": sentiment,
            "positive_mentions": positive_mentions,
            "negative_mentions": negative_mentions,
            "neutral_mentions": neutral_mentions,
            "mentions_total": total_mentions,
            "feature_score": feature_score,
            "source": "amazon",
            "type":"review",
            "evidence": item.get("evidence", "")
        }
        
        if spec_value:
            record["value"] = spec_value

        feature_records.append(record)

    result = {
        "asin": feature_data.get("asin", ""),
        "product": product,
        "features": feature_records
    }
    output_file = f"{OUTPUT_DIR}/{product}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("Saved:", output_file)
    ctr+=1
    print(ctr)'''

##Embeddings generation
DATA_PATH="data/processed_amazon"
COLLECTION_NAME="feature_rag_amazon"

client = chromadb.PersistentClient(path="..\chroma_db")
#client.delete_collection(COLLECTION_NAME)
collection=client.get_or_create_collection(
    name=COLLECTION_NAME
)

#Embedding model
model=SentenceTransformer("intfloat/e5-base-v2")

def build_feature_text(product,feature_data):
    feature=feature_data['feature']
    try:
        value=feature_data["value"]
    except KeyError:
        value=None

    emb= f"""
    Product: {product}
    Feature: {feature_data['feature']}

    Summary:
    The {feature_data['feature']} of {product} is {feature_data['sentiment']} based on user reviews. """

    if value:
        emb+=f"""Specifications: {value}"""

    emb+=f"""
    Review insights:
    Positive mentions: {feature_data['positive_mentions']}, 
    Negative mentions: {feature_data['negative_mentions']}, 
    Neutral mentions: {feature_data['neutral_mentions']},
    Total mentions: {feature_data['mentions_total']}

    Feature score: {feature_data['feature_score']}

    Evidence Example:
    {feature_data['evidence']}
    """
    return emb

def embed_document(text):
    return model.encode(f"passage: {text}", normalize_embeddings=True).tolist()

def embed_query(query):
    return model.encode(f"query: {query}", normalize_embeddings=True).tolist()

#Driver Code
ids=[]
documents=[]
metadatas=[]
embeddings=[]
ctr=0

#Embeddings creation
categories=["laptops", "smartphones"]
for category in categories:
    category_path=os.path.join(DATA_PATH,category)

    for file in os.listdir(category_path):
        file_path=os.path.join(category_path,file)

        with open(file_path,"r", encoding="utf-8") as f:
            data=json.load(f)

        product=data["product"]
        for feature_data in data["features"]:
            doc_id=f"{category}_{product}_{feature_data['feature']}_amazon"
            text=build_feature_text(product, feature_data)
            embedding=embed_document(text)

            metadata={
                "product": product,
                "category": category,
                "feature": feature_data["feature"],
                "sentiment": feature_data["sentiment"],
                "feature_score": feature_data["feature_score"],
                "mentions_total": feature_data["mentions_total"],
                "source": "amazon", #amazon/youtube/specs
                "type": "review" #review/specs
            }
            ctr+=1
            ids.append(doc_id)
            documents.append(text)
            embeddings.append(embedding)
            metadatas.append(metadata)
            print(f"Doc {doc_id} inserted. Ctr: {ctr}")

collection.upsert(ids=ids,documents=documents,embeddings=embeddings,metadatas=metadatas)
print(f"Inserted {len(ids)} feature-level documents into ChromaDB!")
