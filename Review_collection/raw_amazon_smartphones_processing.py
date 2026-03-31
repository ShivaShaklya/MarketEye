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
# FEATURE MAP (IMPROVED)
# -------------------------------
FEATURE_MAP = {
    "battery": ["battery", "charging", "charge", "backup"],
    "display": ["display", "screen", "brightness", "amoled", "lcd"],
    "performance": ["performance", "speed", "processor", "snapdragon", "gaming"],
    "camera": ["camera", "photo", "video", "portrait", "hdr", "night", "selfie"],
    "design": ["design", "build", "weight", "body"],
    "software": ["software", "ui", "android", "ios", "system"],
    "price": ["price", "cost", "value"],
    "speaker": ["speaker", "audio", "sound"],
    "storage": ["storage", "ram", "memory"],
    "thermals": ["heat", "heating", "temperature"],
    "network": ["network", "signal", "5g", "4g"],
    "fingerprint": ["fingerprint"],
}

FEATURE_NORMALIZATION = {
    "charging": "battery"
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
# FEATURE + CONTEXT (FIXED CORE)
# -------------------------------
def extract_features(doc):
    detected = {}

    for token in doc:
        word = token.text.lower()

        for feature, keywords in FEATURE_MAP.items():
            if word in keywords:

                # Use full sentence as base context
                context = token.sent.text

                # Find opinion words linked to feature
                opinion_words = []

                # Children (direct modifiers)
                for child in token.children:
                    if child.pos_ in ["ADJ", "VERB"]:
                        opinion_words.append(child.text)

                # Head relations
                head = token.head
                for child in head.children:
                    if child.pos_ in ["ADJ", "VERB"]:
                        opinion_words.append(child.text)

                # Expand context with opinions
                if opinion_words:
                    context += " " + " ".join(opinion_words)

                detected[feature] = context

    return detected

# -------------------------------
# SENTIMENT (IMPROVED)
# -------------------------------
def analyze_sentiments(contexts):
    results = sentiment_model(contexts)

    sentiments = []
    for r in results:
        label = r["label"]
        score = r["score"]

        # Lower threshold → fewer false neutrals
        if score < 0.45:
            sentiments.append("neutral")
            continue

        if label == "LABEL_2":
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

    for i, sentiment in enumerate(sentiments):
        feature, clause = metadata[i]
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
# PROCESS FOLDER
# -------------------------------
def process_folder(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

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
                if not reviews:
                    continue

                feature_data = process_reviews(reviews)
                output = build_output(feature_data, product_name, asin)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)

                print(f"Processed: {file_name}")

            except Exception as e:
                print(f"Error in {file_name}: {e}")

# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    process_folder("output/smartphones", "output/smartphones_insights_2")