import chromadb
from sentence_transformers import SentenceTransformer
from collections import defaultdict

client = chromadb.PersistentClient(path="./chroma_db")
collection1 = client.get_collection("feature_rag_youtube")
collection2=client.get_collection("rag_product_specifications")

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


'''
##
def embed_query(query):
    model=SentenceTransformer("intfloat/e5-base-v2")
    return model.encode(f"query: {query}", normalize_embeddings=True).tolist()

def pretty_print_results(results, title):
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")

    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for i in range(len(ids)):
        print(f"\nResult {i+1}")
        print(f"ID: {ids[i]}")
        
        if docs:
            print(f"Document: {docs[i][:500]}")  # truncate long text
        
        if metas:
            print(f"Metadata: {metas[i]}")
        
        if dists:
            print(f"Distance (similarity): {dists[i]:.4f}")

        print("-"*40)

#
query = "a phone that can work in sunlight and has a good camera"
query_emb=embed_query(query)

results1 = collection1.query(
    query_embeddings=[query_emb],
    n_results=5
)

results2=collection2.query(
    query_embeddings=[query_emb],
    n_results=5
)

# print(f"\n\nResult 1: {results1}\n\n")
# print(f"\n\nResult 2: {results2}\n\n")

pretty_print_results(results1, "YouTube Features")
pretty_print_results(results2, "Product Specifications")

# for i in range(len(results["ids"][0])):
#     print("\n")
#     print("Product:", results["metadatas"][0][i]["product"])
#     print("Category:", results["metadatas"][0][i]["category"])
#     print("Feature:", results["metadatas"][0][i]["feature"])
#     print("Score:", results["metadatas"][0][i]["feature_score"])
#     print("Distance:", results["distances"][0][i])
#     print("Text:\n", results["documents"][0][i][:500])'''

##
model = SentenceTransformer("intfloat/e5-base-v2")

# -------------------------------
# Embedding
# -------------------------------
def embed_query(query):
    return model.encode(f"query: {query}", normalize_embeddings=True).tolist()

# -------------------------------
# Flatten Results
# -------------------------------
def flatten_results(results):
    items = []

    for i in range(len(results["ids"][0])):
        items.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
            "similarity": 1 - results["distances"][0][i]
        })

    return items

# -------------------------------
# Main Retrieval Function
# -------------------------------
def retrieve_products(query):
    query_emb = embed_query(query)

    # Enforce category filter
    where_filter = {
        "category": "laptops"
    }

    # Query both collections
    results1 = collection1.query(
        query_embeddings=[query_emb],
        n_results=10,
        where=where_filter
    )

    results2 = collection2.query(
        query_embeddings=[query_emb],
        n_results=10,
        where=where_filter
    )

    # Flatten results
    items1 = flatten_results(results1)
    items2 = flatten_results(results2)

    all_items = items1 + items2

    # -------------------------------
    # Merge by product
    # -------------------------------
    products = defaultdict(lambda: {
        "docs": [],
        "max_similarity": 0,
        "features": set(),
        "metadata": {}
    })

    for item in all_items:
        product = item["metadata"]["product"]

        products[product]["docs"].append(item)

        # Track best similarity
        products[product]["max_similarity"] = max(
            products[product]["max_similarity"],
            item["similarity"]
        )

        # Track features (battery, price, etc.)
        if "feature" in item["metadata"]:
            products[product]["features"].add(item["metadata"]["feature"])

        products[product]["metadata"] = item["metadata"]

    # -------------------------------
    # Rank products (embedding-based)
    # -------------------------------
    ranked_products = []

    for product, data in products.items():
        score = data["max_similarity"]

        ranked_products.append({
            "product": product,
            "score": score,
            "features": list(data["features"]),
            "docs": data["docs"]
        })

    ranked_products = sorted(
        ranked_products,
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked_products

# -------------------------------
# Run Example
# -------------------------------
query = "a laptop with a long battery life and windows 11 os"

results = retrieve_products(query)

# -------------------------------
# Pretty Print
# -------------------------------
for i, p in enumerate(results[:10]):
    print(f"\nRank {i+1}: {p['product']}")
    print(f"Score: {p['score']:.4f}")
    print(f"Features Found: {p['features']}")
    print(f"Docs Retrieved: {len(p['docs'])}")
    print("-" * 50)

'''##
model = SentenceTransformer("intfloat/e5-base-v2")

# -------------------------------
# Embedding
# -------------------------------
def embed_query(query):
    return model.encode(f"query: {query}", normalize_embeddings=True).tolist()

# -------------------------------
# Flatten Results
# -------------------------------
def flatten_results(results, query):
    items = []
    query_terms = query.lower().split()

    for i in range(len(results["ids"][0])):
        doc = results["documents"][0][i].lower()

        matched_terms = [q for q in query_terms if q in doc]

        items.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
            "similarity": 1 - results["distances"][0][i],
            "matched_terms": matched_terms,
            "match_score": len(matched_terms)
        })

    return items

# -------------------------------
# Main Retrieval Function
# -------------------------------
def retrieve_products(query):
    query_emb = embed_query(query)

    where_filter = {"category": "smartphones"}

    results1 = collection1.query(
        query_embeddings=[query_emb],
        n_results=10,
        where=where_filter
    )

    results2 = collection2.query(
        query_embeddings=[query_emb],
        n_results=10,
        where=where_filter
    )

    items1 = flatten_results(results1, query)
    items2 = flatten_results(results2, query)

    all_items = items1 + items2

    # -------------------------------
    # Merge by product
    # -------------------------------
    products = defaultdict(lambda: {
        "docs": [],
        "youtube_sim": 0,
        "specs_sim": 0,
        "features": set(),
        "matched_terms": set(),
        "metadata": {}
    })

    for item in all_items:
        product = item["metadata"]["product"]
        source = item["metadata"].get("source")

        products[product]["docs"].append(item)

        if source == "specs":
            products[product]["specs_sim"] = max(
                products[product]["specs_sim"],
                item["similarity"]
            )
        else:
            products[product]["youtube_sim"] = max(
                products[product]["youtube_sim"],
                item["similarity"]
            )

        products[product]["matched_terms"].update(item["matched_terms"])

        if "feature" in item["metadata"]:
            products[product]["features"].add(item["metadata"]["feature"])

        products[product]["metadata"] = item["metadata"]

    # -------------------------------
    # Ranking (FIXED)
    # -------------------------------
    ranked_products = []

    for product, data in products.items():
        specs_sim = data["specs_sim"]
        youtube_sim = data["youtube_sim"]

        # Weighted scoring (specs priority)
        if specs_sim > 0:
            score = 0.7 * specs_sim + 0.3 * youtube_sim
        else:
            score = youtube_sim

        ranked_products.append({
            "product": product,
            "score": score,
            "specs_sim": specs_sim,
            "youtube_sim": youtube_sim,
            "features": list(data["features"]),
            "matched_terms": list(data["matched_terms"]),
            "docs": data["docs"]
        })

    ranked_products = sorted(
        ranked_products,
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked_products

# -------------------------------
# Run Example
# -------------------------------
query = "a laptop with a low price and windows 11 os"

results = retrieve_products(query)

# -------------------------------
# Pretty Print
# -------------------------------
for i, p in enumerate(results[:5]):
    print(f"\nRank {i+1}: {p['product']}")
    print(f"Final Score: {p['score']:.4f}")
    print(f"Specs Sim: {p['specs_sim']:.4f}")
    print(f"YouTube Sim: {p['youtube_sim']:.4f}")
    print(f"Matched Terms: {p['matched_terms']}")
    print(f"Features Found: {p['features']}")

    if p["specs_sim"] > p["youtube_sim"]:
        print("Reason: Strong match from specifications")
    else:
        print("Reason: Strong match from reviews")

    print("-" * 50)'''