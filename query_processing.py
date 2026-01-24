import re
import spacy
from collections import Counter
from gemini_client_setup import call_llm

#Get customer persona and market overview from user query
#Allow cross questioning

nlp = spacy.load("en_core_web_sm")

def idea_confirmation(query, confidence):
    prompt_template="""You are an expert product and startup analyst.
    Given:
    - A processed product idea: {query}
    - A confidence score indicating specificity: {confidence}

    Classify the ideation maturity of the idea using ONLY one of the following stages:
    - exploration
    - problem_framing
    - solution_ideation
    - solution_detailing
    - validation_ready

    Definitions:
    - exploration: vague idea, no clear product or problem
    - problem_framing: problem is clear, solution is not
    - solution_ideation: a solution is proposed but not explained
    - solution_detailing: a solution with mechanisms or implementation details
    - validation_ready: clear solution with target users or market intent

    Then also return:
    1. Ideation stage
    2. Domain of solution
    3. Subdomain of solution
    4. One-line idea description
    5. Short justification for choosing the ideation stage

    Return ONLY valid JSON with exactly these keys:
    {
    "domain": "...",
    "subdomain": "...",
    "ideation_stage": "...",
    "one_line_description": "...",
    "justification": "..."
    }
    No markdown. No extra keys.
    """
    user_message = f"""User query: {query}
    Confidence score (0 to 1): {confidence}
    """
    data=call_llm(prompt_template,user_message)
    required = ["domain", "subdomain", "ideation_stage", "one_line_description","justification"]
    return {k: data[k] for k in required}

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
    
    return confidence

def preprocess_query(query):
    #Convert qury to lowercase and remove special characters
    query=query.strip().lower()
    pattern=r'[^a-z0-9\s]'
    query=re.sub(pattern,'',query)
    
    #Tokenization and lemmatization
    doc=nlp(query)
    processed_query=' '.join([tokens.lemma_ for tokens in doc if not tokens.is_stop])
    print(processed_query)
    confidence_score=calculate_confidence_score(nlp(processed_query))
    print("Score:",confidence_score)

    response_dict=idea_confirmation(processed_query,confidence_score)
    print(response_dict)

#
#query=input("Enter your idea: ")
#query="I am building something very special. Low cost smartphones with a long battery life!!!"
query="I am building something very cool. A low cost smartphones with a long battery life. This will be done by using a solar panel attached to the back of the phone."
preprocess_query(query)
