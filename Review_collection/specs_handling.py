import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

DATA_PATH="data/product_specifications"
COLLECTION_NAME="rag_product_specifications"

client = chromadb.PersistentClient(path="..\chroma_db")
#client.delete_collection(COLLECTION_NAME)
collection=client.get_or_create_collection(
    name=COLLECTION_NAME
)

#Embedding Model
model=SentenceTransformer("intfloat/e5-base-v2")

def normalize_metadata_value(value):
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            return value
    if isinstance(value, list):
        return json.dumps([normalize_metadata_value(item) for item in value])
    if isinstance(value, dict):
        return json.dumps({k: normalize_metadata_value(v) for k, v in value.items()})
    return str(value)

def build_document(file_name,category,data):
    emb=f"{file_name} is a {category}."
    for k,v in data.items():
        if isinstance(v, str):
            emb+=" It has a "+ k.replace("_"," ")+" as "+v+". "
        elif isinstance(v, list):
            for i in v:
                emb+=" It has a "+ k.replace("_"," ")+" as "+i+". It has a "
        else:
            emb+="It has a "+ k.replace("_"," ")+" as "+str(v)+". "
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
        metadata.update({k: normalize_metadata_value(v) for k, v in data.items()})
        ctr+=1
        ids.append(doc_id)
        documents.append(text)
        embeddings.append(embedding)
        metadatas.append(metadata)
        print(f"Doc {doc_id} inserted. Ctr: {ctr}")

collection.upsert(ids=ids,documents=documents,embeddings=embeddings,metadatas=metadatas)
print(f"Inserted {len(ids)} spec documents into ChromaDB!")


