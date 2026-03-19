import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("feature_rag_youtube")

'''#
data = collection.get(include=["metadatas"])

laptops = set()
smartphones = set()

for meta in data["metadatas"]:
    if meta["category"] == "laptops":
        laptops.add(meta["product"])
    elif meta["category"] == "smartphones":
        smartphones.add(meta["product"])

print("Laptop products:", len(laptops))
print("Smartphone products:", len(smartphones))
print("Total products:", len(laptops.union(smartphones)))'''



##
def embed_query(query):
    model=SentenceTransformer("intfloat/e5-base-v2")
    return model.encode(f"query: {query}", normalize_embeddings=True).tolist()

#
query = "a phone with a 32 hr battery life and price less than 10000"

results = collection.query(
    query_embeddings=[embed_query(query)],
    n_results=5
)

for i in range(len(results["ids"][0])):
    print("\n")
    print("Product:", results["metadatas"][0][i]["product"])
    print("Category:", results["metadatas"][0][i]["category"])
    print("Feature:", results["metadatas"][0][i]["feature"])
    print("Score:", results["metadatas"][0][i]["feature_score"])
    print("Distance:", results["distances"][0][i])
    print("Text:\n", results["documents"][0][i][:500])