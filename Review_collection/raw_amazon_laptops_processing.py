import json
import os
import spacy
from collections import defaultdict
from transformers import pipeline

# -------------------------------
# LOAD MODELS
# -------------------------------
nlp = spacy.load("en_core_web_sm")

sentiment_model = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment",
    batch_size=16
)

# -------------------------------
# FEATURE MAP (LAPTOPS)
# -------------------------------
FEATURE_MAP = {
    "battery": ["battery", "charging", "charge"],
    "display": ["display", "screen", "brightness", "panel", "refresh"],
    "performance": ["performance", "speed", "processor", "cpu", "gpu", "lag"],
    "design": ["design", "build", "weight", "body", "finish"],
    "software": ["software", "windows", "os", "drivers", "bios", "system"],
    "price": ["price", "cost", "value"],
    "speaker": ["speaker", "audio", "sound"],
    "storage": ["storage", "ssd", "hdd", "ram", "memory"],
    "thermals": ["heat", "heating", "thermal", "temperature", "overheat"],
    "keyboard": ["keyboard", "keys"],
    "trackpad": ["trackpad", "touchpad"],
    "fan_noise": ["fan", "noise", "loud"],
    "connectivity": ["wifi", "bluetooth", "ports", "usb"],
    "camera": ["webcam", "camera"]
}

FEATURE_NORMALIZATION = {
    "fan": "fan_noise",
    "noise": "fan_noise"
}

CONTRAST_WORDS = {"but", "however", "although", "though", "yet"}

# -------------------------------
# CLEAN PRODUCT NAME
# -------------------------------
def clean_product_name(title):
    return title.split(" - ")[0].strip()

# -------------------------------
# EXTRACT REVIEWS
# -------------------------------
def extract_reviews(data):
    reviews = []
    if "reviews_information" in data:
        block = data["reviews_information"]
        for key in ["authors_reviews", "author_review"]:
            if key in block:
                for r in block[key]:
                    if "text" in r and r["text"].strip():
                        reviews.append(r["text"])
    return reviews

# -------------------------------
# CLAUSE SPLITTING
# -------------------------------
def split_clauses(sentence):
    words = sentence.split()
    clauses, current = [], []

    for w in words:
        if w.lower() in CONTRAST_WORDS:
            if current:
                clauses.append(" ".join(current))
            current = []
        else:
            current.append(w)

    if current:
        clauses.append(" ".join(current))

    return clauses

# -------------------------------
# FEATURE + CONTEXT
# -------------------------------
def extract_features(doc):
    detected = {}

    for token in doc:
        word = token.text.lower()

        for feature, keywords in FEATURE_MAP.items():
            if word in keywords:

                context = token.sent.text
                opinion_words = []

                for child in token.children:
                    if child.pos_ in ["ADJ", "VERB"]:
                        opinion_words.append(child.text)

                head = token.head
                for child in head.children:
                    if child.pos_ in ["ADJ", "VERB"]:
                        opinion_words.append(child.text)

                if opinion_words:
                    context += " " + " ".join(opinion_words)

                detected[feature] = context

    return detected

# -------------------------------
# SENTIMENT
# -------------------------------
def analyze_sentiments(contexts):
    if not contexts:
        return []

    results = sentiment_model(contexts, truncation=True)

    # FIX: normalize output to list
    if isinstance(results, dict):
        results = [results]

    sentiments = []

    for r in results:
        # safety check
        if not isinstance(r, dict):
            sentiments.append("neutral")
            continue

        label = r.get("label", "")
        score = r.get("score", 0)

        if score < 0.45:
            sentiments.append("neutral")
        elif label == "LABEL_2":
            sentiments.append("positive")
        elif label == "LABEL_0":
            sentiments.append("negative")
        else:
            sentiments.append("neutral")

    return sentiments

# -------------------------------
# PROCESS REVIEWS
# -------------------------------
def process_reviews(reviews):
    feature_data = defaultdict(lambda: {
        "positive": set(),
        "negative": set(),
        "neutral": set()
    })

    contexts = []
    metadata = []

    for review in reviews:
        doc = nlp(review)

        for sent in doc.sents:
            clauses = split_clauses(sent.text)

            for clause in clauses:
                clause_doc = nlp(clause)
                features = extract_features(clause_doc)

                for feature, context in features.items():
                    feature = FEATURE_NORMALIZATION.get(feature, feature)

                    contexts.append(context)
                    metadata.append((feature, clause))

    sentiments = analyze_sentiments(contexts)

    for (feature, clause), sentiment in zip(metadata, sentiments):
        feature_data[feature][sentiment].add(clause)

    return feature_data

# -------------------------------
# FINAL SENTIMENT
# -------------------------------
def get_final_sentiment(pos, neg, total):
    if total == 0:
        return "neutral"

    diff = abs(pos - neg)

    if diff / total <= 0.25:
        return "mixed"

    return "positive" if pos > neg else "negative"

# -------------------------------
# BUILD OUTPUT
# -------------------------------
def build_output(feature_data, product_name, asin):
    output_features = []

    for feature, sentiments in feature_data.items():
        pos = list(sentiments["positive"])
        neg = list(sentiments["negative"])
        neu = list(sentiments["neutral"])

        pos_count = len(pos)
        neg_count = len(neg)
        neu_count = len(neu)
        total = pos_count + neg_count + neu_count

        if total == 0:
            continue

        sentiment = get_final_sentiment(pos_count, neg_count, total)
        evidence = " ".join((pos + neg + neu)[:2])

        output_features.append({
            "feature": feature,
            "sentiment": sentiment,
            "positive_mentions": pos_count,
            "negative_mentions": neg_count,
            "neutral_mentions": neu_count,
            "mentions_total": total,
            "feature_score": pos_count - neg_count,
            "source": "amazon",
            "type": "review",
            "evidence": evidence
        })

    return {
        "asin": asin,
        "product": product_name,
        "features": sorted(output_features, key=lambda x: x["mentions_total"], reverse=True),
        "review_summary": "Auto-generated summary from customer reviews."
    }

# -------------------------------
# PROCESS FOLDER (UPDATED)
# -------------------------------
def process_folder(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    skipped_files = []

    for file_name in os.listdir(input_folder):
        if file_name.endswith(".json"):
            input_path = os.path.join(input_folder, file_name)
            output_path = os.path.join(output_folder, file_name.replace(".json", "_insights.json"))

            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                asin = data.get("product_results", {}).get("asin", "unknown")
                title = data.get("product_results", {}).get("title", "unknown_product")
                product_name = clean_product_name(title)

                reviews = extract_reviews(data)

                # 🔴 SKIP FILE IF NO REVIEWS
                if not reviews:
                    skipped_files.append(file_name)
                    print(f"Skipped (no reviews): {file_name}")
                    continue

                feature_data = process_reviews(reviews)
                output = build_output(feature_data, product_name, asin)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)

                print(f"Processed: {file_name}")

            except Exception as e:
                print(f"Error in {file_name}: {e}")

    # -------------------------------
    # SAVE SKIPPED FILES
    # -------------------------------
    if skipped_files:
        log_path = os.path.join(output_folder, "no_reviews.txt")

        with open(log_path, "w", encoding="utf-8") as f:
            for name in skipped_files:
                f.write(name + "\n")

        print(f"\nSkipped files saved to: {log_path}")

# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    process_folder("./data/products/missing_data", "./data/laptops_insights_finalized")  