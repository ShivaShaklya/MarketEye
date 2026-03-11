import json
import os

def match_spec(insight_title):
    insight = insight_title.lower()
    for spec_key, value in normalized_specs.items():
        if any(word in spec_key for word in insight.split()):
            return f"{insight_title}: {value}"
    return insight_title

def normalize_specs(data):
    specs = {}
    specs.update(data.get("product_details", {}))
    return {k.lower().replace("_", " "): v for k, v in specs.items()}

#Driver Code
INPUT_DIR = "data/products/"
OUTPUT_DIR = "data/processed_amazon_products"
os.makedirs(OUTPUT_DIR, exist_ok=True)

for file in os.listdir(INPUT_DIR):
    if not file.endswith(".json"):
        continue

    file_path = os.path.join(INPUT_DIR, file)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    #Get reviews and product specifications
    product = data["product_results"]
    reviews_summary = data["reviews_information"]["summary"]
    try:
        insights = reviews_summary["insights"]
    except KeyError:
        #write name of product to text file and continue
        with open("missing_insights.txt", "a", encoding="utf-8") as log_file:
            log_file.write(f"{file} (ASIN: {product['asin']})\n")
        continue

    #Specs
    specs = {}
    specs.update(data.get("product_details", {}))

    #Preprocessing
    asin = product["asin"]
    title = file.removesuffix(".json")

    normalized_specs = {k.lower().replace("_"," "): v for k,v in specs.items()}

    strengths = []
    weaknesses = []
    mixed_feedback = []

    for item in insights:
        insight_title = item["title"]
        sentiment = item["sentiment"]
        description = match_spec(insight_title)

        if sentiment == "positive":
            strengths.append(description)
        elif sentiment == "negative":
            weaknesses.append(description)
        else:
            mixed_feedback.append(description)

    #Special features extraction ##
    special_features = []
    for key, value in list(normalized_specs.items())[:10]:
        if isinstance(value, str) and len(value) < 60:
            feature = f"{key}: {value}"
            special_features.append(feature)

    #limit to avoid huge feature lists
    #special_features = special_features[:10]

    result = {
        "asin": asin,
        "product_title": title,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "mixed_feedback": mixed_feedback,
        "special_features": special_features,
        "overall_sentiment": reviews_summary["customer_reviews"],
        "review_summary": reviews_summary["text"]
    }


    output_file = f"{OUTPUT_DIR}/{title}_insights.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("Saved:", output_file)