import requests
import os
from dotenv import load_dotenv
import json
from nltk.sentiment import SentimentIntensityAnalyzer

product_names=["Apple AirPods Pro 2",
"iPhone 15 Pro Max",
"Samsung Galaxy S24 Ultra",
"Dell XPS 15 2024",
"Alienware m18"]

key="##Add SERPAPI KEY##"
asin="B0DFD1SHBS"

def get_asin(product_name):
    params = {
        "engine": "amazon",
        "k": product_name,
        "amazon_domain": "amazon.com",
        "api_key": key
    }

    res = requests.get("https://serpapi.com/search", params=params)
    data = res.json()
    asin = data["organic_results"][0]["asin"]
    return asin

def fetch_product_reviews(asin):
    params = {
        "engine": "amazon_product",
        "amazon_domain": "amazon.com",
        "asin": asin,
        "api_key": key
    }
    res = requests.get("https://serpapi.com/search", params=params)
    return res.json()

def save_product(product_name, data):
    os.makedirs("data/products", exist_ok=True)
    safe_name = product_name.replace(" ", "_").lower()
    file_path = f"data/products/{safe_name}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Saved:", product_name)

#Driver Code
for product in product_names:
    asin = get_asin(product)
    data = fetch_product_reviews(asin)
    save_product(product, data)

# ##Search and JSON Extraction
# #load_dotenv("../Backend/.env")
# #SERPAPI_API_KEY=os.getenv("SERPAPI_API_KEY")
# #print("\n\nAPI KEY:\n\n", SERPAPI_API_KEY)

# params={
#     "api_key":key,
#     "engine": "amazon_product",
#     "k":"Apple AirPods Pro 2",
#     "amazon_domain": "amazon.com",
#     "asin": asin
# }

# search=requests.get("https://serpapi.com/search",params=params)
# print(search.url)
# response=search.json()
# print(json.dumps(response, indent=2))

# #Save as JSON
# os.makedirs("data/amazon_products", exist_ok=True)
# file_path = f"data/amazon_products/{asin}.json"
# with open(file_path, "w", encoding="utf-8") as f:
#     json.dump(response, f, indent=2)

# print(f"Saved product data for {asin}")

# ##Review Extraction
# reviews = response["reviews_information"]["authors_reviews"]
# texts = [r["text"] for r in reviews]
# print(texts)

# ##Sentiment Analysis
# sia = SentimentIntensityAnalyzer()
# sentiments = []

# for review in texts:
#     score = sia.polarity_scores(review)
#     sentiments.append(score)

# print(sentiments)


