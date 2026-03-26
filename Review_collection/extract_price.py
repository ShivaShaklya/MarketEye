import json
import os

'''USD_TO_RS_RATE = 83.0
PRODUCTS_DATA_PATH = "data/products"
PRODUCT_SPECS_DATA_PATH = "data/product_specifications"


def _safe_load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _extract_price_metadata(product_data):
    price_usd = product_data.get("product_results", {}).get("extracted_price")
    if price_usd is None:
        return {}

    price_usd = float(price_usd)
    return {
        "price_usd": round(price_usd, 2),
        "price_rs": round(price_usd * USD_TO_RS_RATE, 2),
    }


def _save_price_to_specs(category, file_name, extracted_metadata):
    if not extracted_metadata:
        return

    specs_file_path = os.path.join(PRODUCT_SPECS_DATA_PATH, category, file_name)
    if not os.path.isfile(specs_file_path):
        print("Not found file:", specs_file_path)
        return

    specs_data = _safe_load_json(specs_file_path)
    specs_data.update(extracted_metadata)
    with open(specs_file_path, "w", encoding="utf-8") as file:
        json.dump(specs_data, file, indent=4, ensure_ascii=False)


def load_price_metadata(category):
    category_path = os.path.join(PRODUCTS_DATA_PATH, category)
    if not os.path.isdir(category_path):
        return {}

    price_metadata = {}
    for file_name in os.listdir(category_path):
        if not file_name.endswith(".json"):
            continue

        file_path = os.path.join(category_path, file_name)
        product_data = _safe_load_json(file_path)
        extracted_metadata = _extract_price_metadata(product_data)
        if extracted_metadata:
            price_metadata[file_name.lower()] = extracted_metadata
            _save_price_to_specs(category, file_name, extracted_metadata)

    return price_metadata


if __name__ == "__main__":
    categories = ["laptops", "smartphones"]

    for category in categories:
        category_path = os.path.join(PRODUCTS_DATA_PATH, category)
        if not os.path.isdir(category_path):
            continue

        for file_name in os.listdir(category_path):
            if not file_name.endswith(".json"):
                continue

            file_path = os.path.join(category_path, file_name)
            product_data = _safe_load_json(file_path)
            extracted_metadata = _extract_price_metadata(product_data)
            _save_price_to_specs(category, file_name, extracted_metadata)

##
import serpapi

API_KEY = "c36808b2ce3be13d724c0bde40425bef6d2fbfb761c8ef0f1861a7d4deb8fbe5"
PROCESSED_YOUTUBE_DATA_PATH = r"Review_collection\data\processed_youtube"
PRICE_DB_PATH = r"Review_collection\data\price_db"
DELHI_LOCATION = "Delhi,India"

def _safe_file_name(name):
    return "".join(char.lower() if char.isalnum() else "_" for char in name).strip("_")


def _extract_delhi_price_entries(results):
    candidate_collections = [
        results.get("local_results"),
        results.get("shopping_results"),
        results.get("organic_results"),
        results.get("sellers_results", {}).get("online_sellers"),
        results.get("sellers_results", {}).get("local_sellers"),
    ]
    entries = []
    for collection in candidate_collections:
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict):
                continue
            entry = {
                "position": item.get("position"),
                "seller": item.get("seller") or item.get("source") or item.get("store"),
                "title": item.get("title"),
                "price": item.get("price"),
                "extracted_price": item.get("extracted_price"),
                "currency": item.get("currency"),
                "link": item.get("link") or item.get("product_link"),
                "delivery": item.get("delivery"),
                "rating": item.get("rating"),
                "reviews": item.get("reviews"),
            }
            if any(value is not None for value in entry.values()):
                entries.append(entry)
    return entries


def _fetch_price_metadata(client, product_name):
    results = client.search(
        {
            "engine": "google_shopping",
            "q": product_name,
            "location": DELHI_LOCATION,
            "gl": "in",
            "hl": "en",
        }
    )
    return {
        "product": product_name,
        "location": DELHI_LOCATION,
        "search_metadata": results.get("search_metadata", {}),
        "search_parameters": results.get("search_parameters", {}),
        "price_entries": _extract_delhi_price_entries(results),
    }


def _save_price_metadata(category, product_name, metadata):
    output_dir = os.path.join(PRICE_DB_PATH, category)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{_safe_file_name(product_name)}.json")
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)


def _log_failed_product_name(product_name):
    os.makedirs(PRICE_DB_PATH, exist_ok=True)
    failed_products_path = os.path.join(PRICE_DB_PATH, "failed_products.txt")
    with open(failed_products_path, "a", encoding="utf-8") as file:
        file.write(f"{product_name}\n")

def get_product_names():
    product_names=set()
    for file in os.listdir(r"data/youtube_reviews/smartphones"):
        data=json.load(open(os.path.join(r"data/youtube_reviews/smartphones",file),"r", encoding="utf-8"))
        product=data["product"]
        if product not in product_names:
            product_names.add(product)
    return list(product_names)

#
if __name__ == "__main__":
    client = serpapi.Client(api_key=API_KEY)
    product_names=get_product_names()
    category="smartphones"
    for product_name in product_names:
        metadata = _fetch_price_metadata(client, product_name)
        if not metadata.get("price_entries"):
            _log_failed_product_name(product_name)
            continue
        _save_price_metadata(category, product_name, metadata)
        print("file saved:",product_name)'''
##
import os
import json

PRODUCTS_DATA_PATH = "data/product_prices"
PRODUCT_SPECS_DATA_PATH = "data/product_specifications"


def _safe_load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _extract_price_metadata(product_data):
    price_entries = product_data.get("price_entries", [])

    for entry in price_entries:
        seller = entry.get("seller")
        if seller and seller.lower() == "amazon.in":
            price = entry.get("extracted_price")
            if price:
                return {"price_rs": price}

    return {}  # fallback


def _save_price_to_specs(category, file_name, extracted_metadata):
    if not extracted_metadata:
        print(f"[SKIP] No price for {file_name}")
        return

    specs_file_path = os.path.join(PRODUCT_SPECS_DATA_PATH, category, file_name)

    if not os.path.isfile(specs_file_path):
        print(f"[ERROR] Specs file not found: {specs_file_path}")
        return

    specs_data = _safe_load_json(specs_file_path)

    # Update specs with price
    specs_data.update(extracted_metadata)

    with open(specs_file_path, "w", encoding="utf-8") as file:
        json.dump(specs_data, file, indent=4, ensure_ascii=False)

    print(f"[✔] Updated: {category}/{file_name}")


def process_category(category):
    category_path = os.path.join(PRODUCTS_DATA_PATH, category)

    if not os.path.isdir(category_path):
        print(f"[ERROR] Missing folder: {category_path}")
        return

    for file_name in os.listdir(category_path):
        if not file_name.endswith(".json"):
            continue

        file_path = os.path.join(category_path, file_name)

        try:
            product_data = _safe_load_json(file_path)
        except Exception as e:
            print(f"[ERROR] Failed to load {file_name}: {e}")
            continue

        extracted_metadata = _extract_price_metadata(product_data)
        _save_price_to_specs(category, file_name, extracted_metadata)


if __name__ == "__main__":
    categories = ["laptops", "smartphones"]

    for category in categories:
        process_category(category)