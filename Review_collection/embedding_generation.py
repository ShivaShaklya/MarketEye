import json
import os
import chromadb
from sentence_transformers import SentenceTransformer
from product_spec_preprocessing import *

## 1. Debug specifications
# 2. Create seperate specifications embedding
# 3. Integrate amazon reviews + weighted


DATA_PATH="data/youtube_reviews"
COLLECTION_NAME="feature_rag_youtube"

client = chromadb.PersistentClient(path="./chroma_db")
#client.delete_collection("feature_rag_youtube")
collection=client.get_or_create_collection(
    name=COLLECTION_NAME
)

#Embedding model
model=SentenceTransformer("intfloat/e5-base-v2")

def build_feature_text(product,feature_data):
    feature=feature_data['feature']
    spec_text = get_relevant_specs(product, feature, specs_dict)

    return f"""
    Product: {product}
    Feature: {feature_data['feature']}

    Summary:
    The {feature_data['feature']} of {product} is {feature_data['sentiment']} based on user reviews.

    Specifications:
    {spec_text if spec_text else "NA"}

    Review insights:
    Positive mentions: {feature_data['positive_mentions']}, 
    Negative mentions: {feature_data['negative_mentions']}, 
    Neutral mentions: {feature_data['neutral_mentions']},
    Total mentions: {feature_data['mentions_total']}

    Feature score: {feature_data['feature_score']}

    Evidence Example:
    {feature_data['evidence']}
    """

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

print("Loading Specs")
specs_dict=load_specs("data/products/smartphones")
print(f"Loaded {len(specs_dict)} products")

#Embeddings creation
for category in os.listdir("data/youtube_reviews"):
    category_path=os.path.join(DATA_PATH,category)

    for file in os.listdir(category_path):
        file_path=os.path.join(category_path,file)

        with open(file_path,"r", encoding="utf-8") as f:
            data=json.load(f)

        product=data["product"]
        for feature_data in data["features"]:
            doc_id=f"{category}_{product}_{feature_data['feature']}_youtube"
            text=build_feature_text(product, feature_data)
            embedding=embed_document(text)

            metadata={
                "product": product,
                "category": category,
                "feature": feature_data["feature"],
                "sentiment": feature_data["sentiment"],
                "feature_score": feature_data["feature_score"],
                "mentions_total": feature_data["mentions_total"],
                "source": "youtube",
                "type": "review"
            }
            ctr+=1
            ids.append(doc_id)
            documents.append(text)
            embeddings.append(embedding)
            metadatas.append(metadata)
            print(f"Doc {doc_id} inserted. Ctr: {ctr}")

collection.upsert(ids=ids,documents=documents,embeddings=embeddings,metadatas=metadatas)
print(f"Inserted {len(ids)} feature-level documents into ChromaDB!")
