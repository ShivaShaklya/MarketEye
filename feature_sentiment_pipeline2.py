import json
import re
import sys
import html
from tqdm import tqdm
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

INPUT_FILE = sys.argv[1]
OUTPUT_FILE = sys.argv[2]

sentiment_model = SentimentIntensityAnalyzer()

FEATURES = {
    "camera": ["camera","photo","video","lens"],
    "battery": ["battery","battery life","charging"],
    "display": ["display","screen","brightness"],
    "performance": ["performance","speed","chip","processor"],
    "design": ["design","build","weight","materials"],
    "software": ["ios","software","ui","updates"],
    "price": ["price","cost","expensive","cheap"],
    "speaker": ["speaker","audio","sound"]
}

FILLER_WORDS = [
    "um","uh","you know","like","basically",
    "actually","i mean","sort of","kind of"
]


def clean_transcript(text):

    text = html.unescape(text)

    text = re.sub(r"\[(.*?)\]", " ", text)  # remove [music]
    text = re.sub(r"<.*?>", " ", text)      # remove html

    for word in FILLER_WORDS:
        text = re.sub(rf"\b{word}\b", " ", text, flags=re.IGNORECASE)

    text = re.sub(r"[^a-zA-Z0-9\s\.,!?]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.lower().strip()


def analyze_transcript(text):

    sentences = re.split(r"[.!?]", text)

    feature_results = []

    for feature, keywords in FEATURES.items():

        relevant_sentences = [
            s.strip() for s in sentences
            if any(k in s for k in keywords)
        ]

        if not relevant_sentences:
            continue

        scores = []
        best_sentence = None
        best_score = 0

        for s in relevant_sentences:

            score = sentiment_model.polarity_scores(s)["compound"]
            scores.append(score)

            if abs(score) > abs(best_score):
                best_score = score
                best_sentence = s

        avg = sum(scores) / len(scores)

        if avg > 0.2:
            sentiment = "positive"
        elif avg < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        feature_results.append({
            "feature": feature,
            "sentiment": sentiment,
            "evidence": best_sentence
        })

    return feature_results


def load_jsonl(file_path):

    dataset = []

    with open(file_path, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                dataset.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return dataset


def main():

    dataset = load_jsonl(INPUT_FILE)

    results = []

    print("Processing transcripts...")

    for data in tqdm(dataset):

        transcript = clean_transcript(data.get("transcript",""))

        features = analyze_transcript(transcript)

        results.append({
            "product": data.get("product"),
            "channel": data.get("channel"),
            "source": data.get("source"),
            "features": features
        })

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        json.dump(results,f,indent=2)

    print("Insights saved to", OUTPUT_FILE)


if __name__ == "__main__":
    main()