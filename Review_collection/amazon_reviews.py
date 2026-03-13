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

key="c36808b2ce3be13d724c0bde40425bef6d2fbfb761c8ef0f1861a7d4deb8fbe5"
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


