import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

# Integrate amazon reviews and add weights - amazon reviews pending
# Put category (laptop, smartphone) as a filter in the retrieval step
# understand how scoring is being done
# Rag Validation

DATA_PATH="data/processed_youtube"
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
    try:
        value=feature_data["value"]
    except KeyError:
        value=None

    emb= f"""
    Product: {product}
    Feature: {feature_data['feature']}

    Summary:
    The {feature_data['feature']} of {product} is {feature_data['sentiment']} based on user reviews."""

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
for category in os.listdir("data/processed_youtube"):
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
                "source": "youtube", #amazon/youtube/specs
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
