import requests
import os
from dotenv import load_dotenv
import json
from nltk.sentiment import SentimentIntensityAnalyzer

##Amazon Reviews Scraping using SerpAPI

# product_names=["Apple AirPods Pro 2",
# "iPhone 15 Pro Max",
# "Samsung Galaxy S24 Ultra",
# "Dell XPS 15 2024",
# "Alienware m18"]

load_dotenv()
key=os.getenv("SERPAPI_API_KEY")
#asin="B0DFD1SHBS"

def get_product_names():
    #Use feature_insights_laptops.json
    # product_names=set()
    # with open(r"data/feature_insights_laptops.json", "r", encoding="utf-8") as f:
    #     data = json.load(f)
    #     for item in data:
    #         if item["product"] not in product_names:
    #             product_names.add(item["product"])
    # return list(product_names)

    #Use youtube_reviews folder
    product_names=set()
    for file in os.listdir(r"data/youtube_reviews/smartphones"):
        data=json.load(open(os.path.join(r"data/youtube_reviews/smartphones",file),"r", encoding="utf-8"))
        product=data["product"]
        if product not in product_names:
            product_names.add(product)
    return list(product_names)

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
    os.makedirs("data/products/missing_data/", exist_ok=True)
    safe_name = product_name.replace(" ", "_").lower()
    file_path = f"data/products/missing_data/{safe_name}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Saved:", product_name)

#Driver Code
product_names = list(get_product_names())
# print(product_names)
# print(len(product_names))
#product_names=["xiaomi_13t_pro"]
for product in product_names:
    asin = get_asin(product)
    data = fetch_product_reviews(asin)
    save_product(product, data)


