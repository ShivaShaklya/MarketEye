import json
import os

#Amazon Reviews Processing using summary_insights (Not viable now) : Use <feature_sentiment_nikita> and amazon_embeddings_generation.py instead
def match_spec(feature,normalized_specs):
    words=feature.lower().split()
    for spec_key, value in normalized_specs.items():
        if any(word in spec_key for word in words):
            return value
    return None

def normalize_specs(data):
    specs = {}
    specs.update(data.get("product_details", {}))
    return {k.lower().replace("_", " "): v for k, v in specs.items()}

#Driver Code
INPUT_DIR = "data/products/laptops/"
OUTPUT_DIR = "data/processed_amazon_products/laptops"
os.makedirs(OUTPUT_DIR, exist_ok=True)

for file in os.listdir(INPUT_DIR):
    if not file.endswith(".json"):
        continue

    file_path = os.path.join(INPUT_DIR, file)
    with open(file_path, "r", encoding="utf-8") as f:
        print("Processing:", file)
        data = json.load(f)

    #Get reviews and product specifications
    product = data["product_results"]
    try:
        reviews_summary = data["reviews_information"]["summary"]
    except KeyError:
        #write name of product to text file and continue
        with open("missing_reviews_summary.txt", "a", encoding="utf-8") as log_file:
            log_file.write(f"{file} (ASIN: {product['asin']})\n")
        continue
    
    try:
        insights = reviews_summary["insights"]
    except KeyError:
        #write name of product to text file and continue
        with open("missing_insights.txt", "a", encoding="utf-8") as log_file:
            log_file.write(f"{file} (ASIN: {product['asin']})\n")
        continue

    #Preprocessing
    asin = product["asin"]
    title = file.removesuffix(".json")

    normalized_specs=normalize_specs(data)
    feature_records=[]

    for item in insights:
        feature=item["title"].lower()
        sentiment=item["sentiment"]
        mentions=item.get("mentions",{})

        positive_mentions=mentions.get("positive",0)
        negative_mentions=mentions.get("negative",0)
        total_mentions=mentions.get("total",0)
        if total_mentions==0:
            total_mentions=positive_mentions+negative_mentions
        neutral_mentions=total_mentions-(positive_mentions+negative_mentions)
        
        spec_value=match_spec(feature,normalized_specs)
        record = {
            "feature": feature,
            "sentiment": sentiment,
            "positive_mentions": positive_mentions,
            "negative_mentions": negative_mentions,
            "neutral_mentions": neutral_mentions,
            "mentions_total": total_mentions,
            "feature_score": positive_mentions-negative_mentions,
            "source": "amazon",
            "type":"review",
            "evidence": item.get("summary", "")
        }
        
        if spec_value:
            record["value"] = spec_value

        feature_records.append(record)

    result = {
        "asin": asin,
        "product": title,
        "features": feature_records,
        "overall_sentiment": reviews_summary["customer_reviews"],
        "review_summary": reviews_summary["text"]
    }

    output_file = f"{OUTPUT_DIR}/{title}_insights.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("Saved:", output_file)