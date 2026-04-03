from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_embedding = None
_youtube_db = None
_specs_db = None
_llm = None


def cosine_sim(a: List[float], b: List[float]) -> float:
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def build_search_query(chat: Dict[str, Any]) -> str:
    features: List[str] = []
    idea = chat.get("idea_understanding", {})
    constraints = chat.get("constraints", {})

    for key, value in constraints.items():
        if key == "special_features" and isinstance(value, list):
            features.append("special features: " + ", ".join(value))
        else:
            features.append(f"{key.replace('_', ' ')}: {value}")

    query = f"""
    query: {idea.get('one_line_description', chat.get('idea_raw', ''))}
    important features: {' '.join(features)}
    """
    return query.strip()


def retrieve_products(query: str, k: int = 10):
    youtube_docs = _get_youtube_db().similarity_search(query, k=k)
    spec_docs = _get_specs_db().similarity_search(query, k=k)
    return youtube_docs, spec_docs


def group_by_product(youtube_docs, specs_docs):
    grouped = defaultdict(list)

    for doc in youtube_docs:
        product = doc.metadata.get("product", "Unknown Product")
        grouped[product].append(doc)

    for doc in specs_docs:
        product = doc.metadata.get("product", "Unknown Product")
        grouped[product].append(doc)

    return grouped


def build_product_profiles(grouped_docs) -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}

    for product, docs in grouped_docs.items():
        profile = {"reviews": [], "specs": {}}

        for doc in docs:
            if doc.metadata.get("type") == "review":
                profile["reviews"].append(doc.page_content)

            if doc.metadata.get("type") == "specs":
                for key, value in doc.metadata.items():
                    if key not in {"product", "source", "type"} and key not in profile["specs"]:
                        profile["specs"][key] = value

        profiles[product] = profile

    return profiles


def profile_to_text(profile: Dict[str, Any]) -> str:
    text = ""
    for key, value in profile.get("specs", {}).items():
        text += f"{key}: {value}. "

    text += " ".join(profile.get("reviews", [])[:3])
    return text.strip()


def score_product(profile: Dict[str, Any], constraints: Dict[str, Any]) -> float:
    score = 0.0

    product_text = profile_to_text(profile)
    if product_text:
        product_vec = _get_embedding().embed_query(f"passage: {product_text}")
    else:
        product_vec = []

    for feature in constraints.get("special_features", []):
        if not product_vec:
            break
        feature_vec = _get_embedding().embed_query(f"query: {feature}")
        score += cosine_sim(feature_vec, product_vec)

    budget_raw = constraints.get("budget_price_range")
    price_value = _extract_number(profile.get("specs", {}).get("price"))
    budget_value = _extract_number(budget_raw)
    if budget_value and price_value:
        score += max(0.0, 1 - (price_value / budget_value))

    return round(score, 4)


def rank_products(profiles: Dict[str, Dict[str, Any]], constraints: Dict[str, Any]):
    scored = []
    for product, profile in profiles.items():
        score = score_product(profile, constraints)
        scored.append((product, profile, score))
    return sorted(scored, key=lambda item: item[2], reverse=True)


def generate_report(ranked_products, chat: Dict[str, Any]) -> Dict[str, Any]:
    top_products = ranked_products[:8]
    context = _build_context(top_products)
    prompt = f"""
    You are a market research analyst.

    User Idea:
    Raw Idea: {chat.get('idea_raw')}
    Idea Understanding: {chat.get('idea_understanding')}
    Constraints: {chat.get('constraints')}

    Competitor Data:
    {context}

    Generate a detailed report including:
    1. Top competing products
    2. Competitor strengths and weaknesses
    3. Market gaps
    4. Feasibility of the idea
    5. Challenges in implementation

    IMPORTANT RULES:
    - Base your analysis primarily on the provided competitor data.
    - You may use general knowledge only for feasibility reasoning.
    - Return ONLY valid JSON.

    Schema:
    {{
      "top_competitors": [
        {{
          "product_name": "...",
          "price": "...",
          "key_features": ["..."],
          "strengths": ["..."],
          "weaknesses": ["..."]
        }}
      ],
      "market_gap_analysis": {{
        "existing_gaps": ["..."],
        "unmet_features": ["..."],
        "opportunity_level": "low | medium | high"
      }},
      "feasibility_analysis": {{
        "is_feasible": true,
        "reasoning": "...",
        "technical_challenges": ["..."],
        "cost_constraints": ["..."]
      }},
      "implementation_challenges": ["..."]
    }}
    """

    response = _get_llm().invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    data = _extract_json(content)

    return {
        "search_query": build_search_query(chat),
        "retrieved_products": [
            {
                "product_name": product,
                "score": score,
                "specs": profile.get("specs", {}),
                "review_count": len(profile.get("reviews", [])),
            }
            for product, profile, score in top_products
        ],
        "analysis": data,
    }


def run_rag(chat: Dict[str, Any], k: int = 10) -> Dict[str, Any]:
    query = build_search_query(chat)
    youtube_docs, specs_docs = retrieve_products(query, k=k)
    grouped = group_by_product(youtube_docs, specs_docs)
    profiles = build_product_profiles(grouped)
    ranked = rank_products(profiles, chat.get("constraints", {}))
    if not ranked:
        result = {
            "search_query": query,
            "retrieved_products": [],
            "analysis": {
                "top_competitors": [],
                "market_gap_analysis": {
                    "existing_gaps": ["No competitor records were retrieved from the current vector stores."],
                    "unmet_features": [],
                    "opportunity_level": "unknown",
                },
                "feasibility_analysis": {
                    "is_feasible": False,
                    "reasoning": "The RAG pipeline could not retrieve enough evidence to assess feasibility.",
                    "technical_challenges": [],
                    "cost_constraints": [],
                },
                "implementation_challenges": ["Populate the Chroma collections before running competitor analysis."],
            },
        }
        save_report(chat, result)
        return result
    result = generate_report(ranked, chat)
    save_report(chat, result)
    return result


def format_rag_summary(rag_result: Dict[str, Any]) -> str:
    analysis = rag_result.get("analysis", {})
    competitors = analysis.get("top_competitors", [])
    market_gap = analysis.get("market_gap_analysis", {})
    feasibility = analysis.get("feasibility_analysis", {})
    challenges = analysis.get("implementation_challenges", [])

    parts = ["## Competitive Analysis"]

    if competitors:
        parts.append("\n### Top Competitors")
        for item in competitors[:3]:
            strengths = ", ".join(item.get("strengths", [])[:2]) or "N/A"
            weaknesses = ", ".join(item.get("weaknesses", [])[:2]) or "N/A"
            parts.append(
                f"- **{item.get('product_name', 'Unknown')}** | Price: {item.get('price', 'N/A')} | "
                f"Strengths: {strengths} | Weaknesses: {weaknesses}"
            )

    if market_gap:
        parts.append("\n### Market Gaps")
        parts.append(
            f"**Opportunity Level**: {market_gap.get('opportunity_level', 'unknown').title()}"
        )
        for gap in market_gap.get("existing_gaps", [])[:3]:
            parts.append(f"- {gap}")

    if feasibility:
        parts.append("\n### Feasibility")
        parts.append(f"**Feasible**: {'Yes' if feasibility.get('is_feasible') else 'No'}")
        parts.append(feasibility.get("reasoning", "No reasoning provided."))

    if challenges:
        parts.append("\n### Implementation Challenges")
        for challenge in challenges[:4]:
            parts.append(f"- {challenge}")

    return "\n".join(parts)


def save_report(chat: Dict[str, Any], rag_result: Dict[str, Any]) -> Path:
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    file_path = reports_dir / f"{chat.get('user_id', 'user')}_{chat.get('chat_id', 'chat')}_rag.json"
    payload = {"input": chat.get("idea_raw", ""), "response": rag_result}
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def _build_context(top_products) -> str:
    blocks = []
    for product, profile, score in top_products:
        blocks.append(
            "\n".join(
                [
                    f"Product: {product}",
                    f"Specs: {profile.get('specs', {})}",
                    f"Sample Reviews: {' '.join(profile.get('reviews', [])[:3])}",
                    f"Score: {score}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _extract_number(value: Any) -> int | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def _extract_json(text: str) -> Dict[str, Any]:
    if isinstance(text, list):
        text = " ".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in text
        )
    text = str(text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            return json.loads(text[start:end + 1])
        raise


def _get_embedding():
    global _embedding
    if _embedding is None:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        _embedding = HuggingFaceEmbeddings(model_name="intfloat/e5-base-v2")
    return _embedding


def _get_youtube_db():
    global _youtube_db
    if _youtube_db is None:
        from langchain_community.vectorstores import Chroma

        _youtube_db = Chroma(
            collection_name="feature_rag_youtube",
            embedding_function=_get_embedding(),
            persist_directory=str(PROJECT_ROOT / "chroma_db"),
        )
    return _youtube_db


def _get_specs_db():
    global _specs_db
    if _specs_db is None:
        from langchain_community.vectorstores import Chroma

        _specs_db = Chroma(
            collection_name="rag_product_specifications",
            embedding_function=_get_embedding(),
            persist_directory=str(PROJECT_ROOT / "chroma_db"),
        )
    return _specs_db


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("API-KEY")
        _llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            api_key=api_key,
            temperature=0.2,
        )
    return _llm


if __name__ == "__main__":
    sample_chat = PROJECT_ROOT / "chats" / "sample.json"
    if sample_chat.exists():
        print(run_rag(json.loads(sample_chat.read_text(encoding="utf-8"))))
    else:
        print("Pass a real chat dict from the app; no hardcoded execution is configured.")
