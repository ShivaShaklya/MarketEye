import json
import os

'''def match_spec(feature, normalized_specs):
    words=feature.lower().split()
    matches=[]
    for spec_key, value in normalized_specs.items():
        if any(word in spec_key for word in words):
            matches.append(f"{spec_key}: {value}")
    return matches if matches else None

def normalize_specs(data):
    specs={}
    specs.update(data.get("product_details",{}))
    return {k.lower().replace("_"," "): v for k,v in specs.items()}

#Driver Code
youtube_path="data/youtube_reviews/smartphones"
specs_input="data/products/smartphones"
output_dir= "data/processed_youtube/smartphones"

os.makedirs(output_dir,exist_ok=True)

for file in os.listdir(youtube_path):
    if not file.endswith(".json"):
        continue
    
    with open(os.path.join(specs_input, file.replace(" ","_").lower()), "r", encoding="utf-8") as f:
        print("opening specs file for:", file)
        p_specs= json.load(f)

    product_name = file.replace(".json", "").lower()
    normalized_specs=normalize_specs(p_specs)

    try:
        with open(os.path.join(youtube_path, file), "r", encoding="utf-8") as f:
            youtube_product=json.load(f)
            print("Processing:", file)
    except:
        print("\n\nNo youtube file for: ", file)
        continue

    # MATCH FEATURES WITH SPECS
    for feature in youtube_product["features"]:
        feature_name = feature["feature"]
        spec_value = match_spec(feature_name, normalized_specs)
        if spec_value:
            feature["value"] = spec_value

    output_file = os.path.join(output_dir, file)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(youtube_product, f, indent=2)
    print("Saved:", output_file)

##Youtube reviews sentiment (Adding mixed sentiment)
def get_sentiment(pos, neg, total, original_sentiment):
    if total == 0:
        return original_sentiment

    #For mixed
    diff = abs(pos - neg)
    if diff / total <= 0.3:
        print("mixed")
        return "mixed"
    
    return original_sentiment

#Driver Code
youtube_path="data/processed_youtube/smartphones"
for file in os.listdir(youtube_path):
    with open(os.path.join(youtube_path,file)) as f:
        data=json.load(f)

    modified = False 
    for feature in data["features"]:
        positive_mentions = feature.get("positive_mentions", 0)
        negative_mentions = feature.get("negative_mentions", 0)
        total_mentions = feature.get("mentions_total", 0)

        sentiment = get_sentiment(
            positive_mentions,
            negative_mentions,
            total_mentions,
            feature["sentiment"]
        )
        if sentiment=="mixed":
            feature['sentiment']=sentiment
            modified=True
            print("mixed in:", file, "| feature:", feature["feature"])

        if modified:
            with open(os.path.join(youtube_path,file), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)'''

##Product specifications seperate json creation
import json
import os

os.makedirs("data/product_specifications/laptops",exist_ok=True)

data_path="data/products/laptops"
specs_path="data/product_specifications/laptops"
specs_dict={}
for file in os.listdir(data_path):
    with open(os.path.join(data_path,file),"r",encoding="utf-8") as f:
        data=json.load(f)

    try:
        for k,v in data["product_details"].items():
            if k in ["asin","customer_reviews","rating","reviews","best_sellers_rank"]:
                continue
            else:
                specs_dict[k]=v
    except KeyError:
        with open("log_file.txt", "a", encoding="utf-8") as log_file:
            log_file.write(f"{file}\n")
            continue
    with open(os.path.join(specs_path,file),"x") as f1:
        json.dump(specs_dict,f1,indent=2)
        print("File saved:", file)
        specs_dict={}
        continue

        




