import re
import spacy
from collections import Counter

#Setup google gemini
#Get domain, subdomain, ideation stage and one line description from user query
#Get customer persona and market overview from user query
#Allow cross questioning

nlp = spacy.load("en_core_web_sm")

def calculate_confidence_score(doc):
    #Semantic focus
    noun_chunks = [chunk.root.lemma_ for chunk in doc.noun_chunks]
    if not noun_chunks:
        return 0.0
    counts = Counter(noun_chunks)
    top_ratio = counts.most_common(1)[0][1] / len(noun_chunks)
    semantic_focus_score=round(top_ratio, 2)

    #Product clarity
    product_nouns = 0
    for token in doc:
        if token.pos_=="NOUN" and token.dep_ in ["dobj", "pobj", "nsubj"]:
            product_nouns+=1
    product_clarity_score=min(product_nouns/3, 1.0)

    #Details and constraints
    constraints=0
    for token in doc:
        if token.pos_=="ADJ":
            constraints+=1
        if token.text in ["battery", "cost", "price", "power", 'speed', 'camera', 'size', 'weight']:
            constraints+=1
    constraint_score=min(constraints/4, 1.0)

    #Noise penalty
    vague_terms={"something", "thing", "stuff", "cool", "special", "nice"}
    noise=sum(1 for t in doc if t.lemma_ in vague_terms)
    noise_score=max(0.0, 1.0 - (noise * 0.25))

    scores = {
        "focus": semantic_focus_score,
        "product": product_clarity_score,
        "constraints": constraint_score,
        "noise":noise_score,
    }

    confidence = (
        scores["focus"] * 0.25 +
        scores["product"] * 0.25 +
        scores["constraints"] * 0.25 +
        scores["noise"] * 0.25
        #scores["length"] * 0.2
    )

    return round(confidence, 2)

def preprocess_query(query):
    #Convert qury to lowercase and remove special characters
    query=query.strip().lower()
    pattern=r'[^a-z0-9\s]'
    query=re.sub(pattern,'',query)
    
    #Tokenization and lemmatization
    doc=nlp(query)
    processed_query=' '.join([tokens.lemma_ for tokens in doc if not tokens.is_stop])
    print(processed_query)
    print("Score:",calculate_confidence_score(nlp(processed_query)))

#
#query=input("Enter your idea: ")
#query="I am building something very special. Low cost smartphones with a long battery life!!!"
query="I am building something very cool. A low cost smartphones with a long battery life. This will be done by using a solar panel attached to the back of the phone."
preprocess_query(query)
