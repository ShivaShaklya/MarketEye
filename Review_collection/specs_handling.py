import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

DATA_PATH="data/product_specifications"
COLLECTION_NAME="rag_product_specifications"

client = chromadb.PersistentClient(path="./chroma_db")
#client.collection.delete(where={"source": "specs"})
collection=client.get_or_create_collection(
    name=COLLECTION_NAME
)

#Embedding Model
model=SentenceTransformer("intfloat/e5-base-v2")

def build_document(file_name,category,data):
    emb=f"{file_name} is a {category}. It has a "
    for k,v in data.items():
        if isinstance(v, str):
            emb+=k+" as "+v+". It has a "
        elif isinstance(v, list):
            for i in v:
                emb+=k+" as "+i+". It has a "
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

    for file in os.listdir("data/processed_youtube/"+category):
        file_path=os.path.join(category_path,file.lower().replace(" ","_"))

        with open(file_path,"r", encoding="utf-8") as f:
            data=json.load(f)

        product=file.replace(".json", "")
        doc_id=f"{category}_{product}_specs"
        text=build_document(product, category, data)
        embedding=embed_document(text)

        metadata={
            "product": product,
            "category": category,
            "source": "specs", #amazon/youtube/specs
            "type": "specs" #review/specs
        }
        ctr+=1
        ids.append(doc_id)
        documents.append(text)
        embeddings.append(embedding)
        metadatas.append(metadata)
        print(f"Doc {doc_id} inserted. Ctr: {ctr}")

collection.upsert(ids=ids,documents=documents,embeddings=embeddings,metadatas=metadatas)
print(f"Inserted {len(ids)} spec documents into ChromaDB!")


