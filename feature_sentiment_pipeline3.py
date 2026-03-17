import json
import re
import sys
import html
from collections import defaultdict
from tqdm import tqdm
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

INPUT_FILE = sys.argv[1]
OUTPUT_FILE = sys.argv[2]

sentiment_model = SentimentIntensityAnalyzer()

# Canonical product features
FEATURES = {
    "camera": ["camera","photo","photos","video","lens","zoom","portrait"],
    "battery": ["battery","battery life","charging","charge","fast charge"],
    "display": ["display","screen","brightness","refresh rate","panel"],
    "performance": ["performance","speed","chip","processor","gaming","lag"],
    "design": ["design","build","weight","materials","finish"],
    "software": ["ios","android","software","ui","updates"],
    "price": ["price","cost","expensive","cheap","value"],
    "speaker": ["speaker","audio","sound"],
    "storage": ["storage","memory","ram","ssd"],
    "thermals": ["heat","cooling","thermal","temperature"]
}

FILLERS = [
    "um","uh","you know","like","basically",
    "actually","i mean","sort of","kind of"
]


# -----------------------------
# Transcript Cleaning
# -----------------------------
def clean_transcript(text):

    text = html.unescape(text)

    text = re.sub(r"\[(.*?)\]", " ", text)   # remove [music]
    text = re.sub(r"<.*?>", " ", text)       # remove html tags

    for f in FILLERS:
        text = re.sub(rf"\b{f}\b", " ", text, flags=re.IGNORECASE)

    text = re.sub(r"[^a-zA-Z0-9\s\.,!?]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.lower().strip()


# -----------------------------
# Sentence Sentiment
# -----------------------------
def sentence_sentiment(sentence):

    score = sentiment_model.polarity_scores(sentence)["compound"]

    if score > 0.2:
        return "positive"
    elif score < -0.2:
        return "negative"

    return "neutral"


# -----------------------------
# Detect features in sentence
# -----------------------------
def detect_features(sentence):

    found = []

    for feature, keywords in FEATURES.items():

        for k in keywords:

            if k in sentence:
                found.append(feature)
                break

    return found


# -----------------------------
# Load JSONL
# -----------------------------
def load_jsonl(path):

    rows = []

    with open(path,"r",encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return rows


# -----------------------------
# Main Pipeline
# -----------------------------
def main():

    data = load_jsonl(INPUT_FILE)

    products = {}

    for row in tqdm(data):

        product = row.get("product")
        asin = row.get("asin","unknown")
        source = row.get("source","youtube")

        transcript = clean_transcript(row.get("transcript",""))

        sentences = re.split(r"[.!?]", transcript)

        if product not in products:

            products[product] = {
                "asin": asin,
                "product": product,
                "features": defaultdict(list)
            }

        for s in sentences:

            if len(s.split()) < 5:
                continue

            detected = detect_features(s)

            if not detected:
                continue

            sent = sentence_sentiment(s)

            for f in detected:

                products[product]["features"][f].append({
                    "sentiment": sent,
                    "evidence": s,
                    "source": source
                })


    output = []

    for product, pdata in products.items():

        features_out = []

        for feature, mentions in pdata["features"].items():

            pos = sum(1 for m in mentions if m["sentiment"]=="positive")
            neg = sum(1 for m in mentions if m["sentiment"]=="negative")
            neu = sum(1 for m in mentions if m["sentiment"]=="neutral")

            total = pos + neg + neu
            score = pos - neg

            if pos > neg:
                sentiment = "positive"
            elif neg > pos:
                sentiment = "negative"
            elif pos == neg and pos > 0:
                sentiment = "mixed"
            else:
                sentiment = "neutral"

            evidence = mentions[0]["evidence"]

            features_out.append({
                "feature": feature,
                "sentiment": sentiment,
                "positive_mentions": pos,
                "negative_mentions": neg,
                "neutral_mentions": neu,
                "mentions_total": total,
                "feature_score": score,
                "source": mentions[0]["source"],
                "type": "transcript",
                "evidence": evidence
            })

        # sort features alphabetically
        features_out = sorted(features_out, key=lambda x: x["feature"])

        # build short summary
        summary_parts = []

        for f in features_out[:3]:
            summary_parts.append(f["evidence"])

        review_summary = " ".join(summary_parts)

        output.append({
            "asin": pdata["asin"],
            "product": product,
            "features": features_out,
            "review_summary": review_summary
        })


    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        json.dump(output,f,indent=2)

    print("Product insights saved to", OUTPUT_FILE)


if __name__ == "__main__":
    main()