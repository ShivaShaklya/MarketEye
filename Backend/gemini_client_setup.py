from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple

load_dotenv()
api_key1=os.getenv("API-KEY")
client=genai.Client(api_key=api_key1)

#
def call_llm(prompt_template: str, user_message: str, history_contents: Optional[List[Dict[str,Any]]]=None) -> Tuple[Dict[str,Any], List[Dict[str,Any]]]:

    contents: List[Dict[str,Any]]=[]
    if history_contents:
        contents.extend(history_contents)

    contents.append({"role":"user","parts":[{"text":user_message}]})

    response=client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=contents,
        config={
            "system_instruction": prompt_template,
            "response_mime_type":"application/json"
        },
    )

    text=(response.text or "").strip()
    try:
        data=json.loads(text)
        contents.append({"role":"model","parts":[{"text":text}]})
        return data,contents
    except:
        raise ValueError("Incorrect output format by LLM. Raw output:\n",text)
    
def format_list(items):
    return "\n- " + "\n- ".join(items) if items else "None"


def _generate_json_response(
    *,
    model: str,
    contents: Any,
    config: Any,
    retries: int = 2,
    retry_delay_seconds: float = 1.5,
) -> Dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            text = (response.text or "").strip()
            return json.loads(text)
        except Exception as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(retry_delay_seconds * (attempt + 1))

    raise ValueError(f"Incorrect output format by LLM or model request failed. Raw error: {last_error}")
    
def call_llm_ideal_product_outline(input_data: Dict[str, Any]):
    idea = input_data["idea_raw"]
    idea_understanding = input_data["idea_understanding"]
    constraints = input_data["constraints"]

    top_competitors = input_data["top_competitors"]
    market_gap_analysis = input_data["market_gap_analysis"]
    feasibility_analysis = input_data["feasibility_analysis"]
    implementation_challenges = input_data["implementation_challenges"]

    prompt_template = f"""
    You are a product strategy analyst.
    Analyze the following structured business idea and produce an ideal product outline grounded in the provided evidence.

    IDEA OVERVIEW:
    - Raw Idea: {idea}
    - Domain: {idea_understanding['domain']}
    - Subdomain: {idea_understanding['subdomain']}
    - Stage: {idea_understanding['ideation_stage']}
    - Description: {idea_understanding['one_line_description']}

    CONSTRAINTS:
    {constraints}

    TOP COMPETITORS:
    {json.dumps(top_competitors, indent=2)}

    MARKET GAP ANALYSIS:
    Existing Gaps: {format_list(market_gap_analysis['existing_gaps'])}
    Unmet Features: {format_list(market_gap_analysis['unmet_features'])}
    Opportunity Level: {market_gap_analysis.get('opportunity_level', 'unknown')}

    FEASIBILITY ANALYSIS:
    Feasible: {feasibility_analysis.get('is_feasible', 'unknown')}
    Reasoning: {feasibility_analysis.get('reasoning', '')}
    Technical Challenges: {format_list(feasibility_analysis['technical_challenges'])}
    Cost Constraints: {format_list(feasibility_analysis['cost_constraints'])}

    IMPLEMENTATION CHALLENGES:
    {format_list(implementation_challenges)}

    Provide the output as a single valid JSON object:
    {{
        "IdealProductOutline": {{
            "core_product_vision": "...",
            "target_customer": "...",
            "must_have_features": ["..."],
            "recommended_differentiators": ["..."],
            "pricing_and_positioning": ["..."],
            "launch_considerations": ["..."]
        }},
        "EndStatement": "A concise summary of the best product direction to pursue, based on the business idea, market gap analysis, feasibility analysis, and implementation challenges."
    }}

    Ensure that:
    - The outline is specific and grounded in the provided inputs.
    - Must-have features should reflect the strongest user needs and market gaps.
    - Pricing and positioning should align with the stated constraints and competitor landscape.
    - Launch considerations should mention the biggest feasibility or implementation constraints.
    - Avoid generic or vague statements. 
    - The response must be strictly valid JSON with no additional text outside the JSON object.
    """

    return _generate_json_response(
        model="gemini-flash-latest",
        contents=prompt_template,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    )


def call_llm_swot(input_data: Dict[str, Any]) -> Dict[str, Any]:
    idea = input_data["idea_raw"]
    idea_understanding = input_data["idea_understanding"]
    constraints = input_data["constraints"]

    top_competitors = input_data["top_competitors"]
    market_gap_analysis = input_data["market_gap_analysis"]
    feasibility_analysis = input_data["feasibility_analysis"]
    implementation_challenges = input_data["implementation_challenges"]

    prompt_template = f"""
    You are a business analyst. Analyze the following structured business idea and generate a SWOT analysis and a market report.

    IDEA OVERVIEW:
    - Raw Idea: {idea}
    - Domain: {idea_understanding['domain']}
    - Subdomain: {idea_understanding['subdomain']}
    - Stage: {idea_understanding['ideation_stage']}
    - Description: {idea_understanding['one_line_description']}

    CONSTRAINTS:
    {constraints}

    TOP COMPETITORS:
    {json.dumps(top_competitors, indent=2)}

    MARKET GAP ANALYSIS:
    Existing Gaps: {format_list(market_gap_analysis['existing_gaps'])}
    Unmet Features: {format_list(market_gap_analysis['unmet_features'])}
    Opportunity Level: {market_gap_analysis.get('opportunity_level', 'unknown')}

    FEASIBILITY ANALYSIS:
    Feasible: {feasibility_analysis.get('is_feasible', 'unknown')}
    Reasoning: {feasibility_analysis.get('reasoning', '')}
    Technical Challenges: {format_list(feasibility_analysis['technical_challenges'])}
    Cost Constraints: {format_list(feasibility_analysis['cost_constraints'])}

    IMPLEMENTATION CHALLENGES:
    {format_list(implementation_challenges)}

    Provide the output as a single valid JSON object:
    {{
        "SWOT": {{
            "Strengths": ["..."],
            "Weaknesses": ["..."],
            "Opportunities": ["..."],
            "Threats": ["..."]
        }},
        "EndStatement": "A concise summary of the market potential and viability of the business idea, based on the business idea, market gap analysis, feasibility analysis, and implementation challenges."
    }}

    Ensure that:
    - All SWOT points are specific and grounded in the provided inputs.
    - Avoid generic or vague statements.
    - The response must be strictly valid JSON with no additional text outside the JSON object.
    """

    return _generate_json_response(
        model="gemini-flash-latest",
        contents=prompt_template,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    )


def call_llm_grounded_grants(input_data: Dict[str, Any]) -> Dict[str, Any]:
    prompt_template = f"""
    You are a startup funding analyst.

    Your task is to find REAL and CURRENT grant, funding, accelerator, incubator, or innovation-support programs
    that are relevant to the product idea below.

    IMPORTANT RULES:
    - Use Google Search grounding.
    - Only include opportunities that appear to actually exist based on grounded search results.
    - Only include an item when you can provide a citation-backed source title and source URL.
    - Do not invent grant names, providers, eligibility rules, or links.
    - Prefer official program pages or clearly attributable institutional sources.
    - If nothing clearly relevant is found, return an empty grants array.
    - Return strictly valid JSON and nothing else.

    PRODUCT CONTEXT:
    {json.dumps(input_data, ensure_ascii=False, indent=2)}

    Return JSON in exactly this shape:
    {{
      "grants": [
        {{
          "program_name": "...",
          "provider": "...",
          "why_it_may_fit": "...",
          "eligibility_hint": "...",
          "source_title": "...",
          "source_url": "..."
        }}
      ],
      "notes": ["..."]
    }}
    """

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt_template,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    text = (response.text or "").strip()
    try:
        data = json.loads(text)
    except Exception:
        raise ValueError("Incorrect output format by LLM. Raw output:\n", text)

    grounded_sources = _extract_grounded_sources(response)
    data["grants"] = _filter_grounded_grants(data.get("grants", []), grounded_sources)
    if not data["grants"]:
        data["notes"] = []
    else:
        data["notes"] = [note for note in data.get("notes", []) if str(note).strip()]
    return data


def _extract_grounded_sources(response) -> List[Dict[str, str]]:
    sources: List[Dict[str, str]] = []
    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        metadata = getattr(candidate, "grounding_metadata", None)
        chunks = getattr(metadata, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue
            title = (getattr(web, "title", "") or "").strip()
            url = (getattr(web, "uri", "") or "").strip()
            if not url:
                continue
            sources.append({
                "title": title,
                "url": url,
            })

    unique: List[Dict[str, str]] = []
    seen = set()
    for item in sources:
        key = _normalize_url(item["url"])
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _filter_grounded_grants(grants: Any, grounded_sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if not isinstance(grants, list) or not grounded_sources:
        return []

    by_url = {
        _normalize_url(source["url"]): source
        for source in grounded_sources
        if source.get("url")
    }
    by_title = {
        _normalize_title(source["title"]): source
        for source in grounded_sources
        if source.get("title")
    }

    verified: List[Dict[str, str]] = []
    seen_programs = set()

    for item in grants:
        if not isinstance(item, dict):
            continue

        raw_url = str(item.get("source_url", "") or "").strip()
        raw_title = str(item.get("source_title", "") or "").strip()

        matched = None
        if raw_url:
            matched = by_url.get(_normalize_url(raw_url))
        if matched is None and raw_title:
            matched = by_title.get(_normalize_title(raw_title))
        if matched is None:
            continue

        program_name = str(item.get("program_name", "") or "").strip()
        provider = str(item.get("provider", "") or "").strip()
        if not program_name or not provider:
            continue

        program_key = (program_name.lower(), _normalize_url(matched["url"]))
        if program_key in seen_programs:
            continue
        seen_programs.add(program_key)

        verified.append({
            "program_name": program_name,
            "provider": provider,
            "why_it_may_fit": str(item.get("why_it_may_fit", "") or "").strip(),
            "eligibility_hint": str(item.get("eligibility_hint", "") or "").strip(),
            "source_title": matched.get("title", raw_title),
            "source_url": matched.get("url", raw_url),
        })

    return verified


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/").lower()


def _normalize_title(value: str) -> str:
    return " ".join(value.strip().lower().split())
    
if __name__=="__main__":
    input_data = {
        "idea_raw": "I'm building a low-cost smartphone with solar charging for rural markets.",

        "idea_understanding": {
            "domain": "Hardware/Energy",
            "subdomain": "Mobile Charging/Renewable Energy",
            "ideation_stage": "solution_design and solution_detailing",
            "one_line_description": "Develop a low-cost smartphone solar charging solution targeted at rural markets.",
            "justification": "The query specifies a clear solution (low-cost smartphone solar charging) and a target market (rural), moving beyond exploration into design."
        },

        "constraints": {
            "budget_price_range": "under 30000 INR",
            "geolocation": "rural market",
            "special_features": ["solar charging"],
            "feature_priority": "cost",
            "distribution_preference": "both",
            "buyer_preference": "offline"
        },

        "top_competitors": [
            {
                "product_name": "Samsung Galaxy A34",
                "price": "32,999 INR",
                "key_features": [
                    "5000 mAh Battery",
                    "41 Hours Talk Time",
                    "6.5 Inch Display",
                    "IP67 Water Resistance"
                ],
                "strengths": [
                    "Exceeds 32-hour battery requirement",
                    "Strong offline presence in rural markets"
                ],
                "weaknesses": [
                    "Above budget",
                    "No solar charging"
                ],
                "competitive_score": 8.5
            },
            {
                "product_name": "OnePlus 11",
                "price": "32,999 INR",
                "key_features": [
                    "7300 mAh Battery",
                    "Fast charging",
                    "12 GB RAM"
                ],
                "strengths": [
                    "Very high battery capacity",
                    "Fast charging tech"
                ],
                "weaknesses": [
                    "Heavy device",
                    "Fragile for rural use"
                ],
                "competitive_score": 8.2
            },
            {
                "product_name": "Samsung Galaxy S24",
                "price": "48,999 INR",
                "key_features": [
                    "4000 mAh Battery",
                    "AMOLED Display",
                    "5G"
                ],
                "strengths": [
                    "Premium quality",
                    "Good software support"
                ],
                "weaknesses": [
                    "Too expensive",
                    "Battery insufficient",
                    "No solar"
                ],
                "competitive_score": 4.5
            }
        ],

        "market_gap_analysis": {
            "existing_gaps": [
                "No smartphones with integrated solar charging",
                "Lack of devices for off-grid rural usage",
                "High battery phones exceed budget"
            ],
            "unmet_features": [
                "Passive solar charging",
                "Long standby for low-electricity regions",
                "Rugged affordable design"
            ],
            "opportunity_level": "high"
        },

        "feasibility_analysis": {
            "is_feasible": True,
            "reasoning": "Solar integration is possible but limited to trickle charging; aligns with rural needs.",
            "technical_challenges": [
                "Limited solar power generation due to small surface",
                "Heat management issues",
                "Maintaining slim design"
            ],
            "cost_constraints": [
                "Solar components increase cost",
                "Trade-offs in camera/processor needed"
            ]
        },

        "implementation_challenges": [
            "Low solar efficiency (15–20 hrs charging)",
            "Durability of solar panel",
            "User expectation mismatch",
            "Thermal management",
            "Rural distribution and servicing"
        ]
    }
    outline_and_report = call_llm_ideal_product_outline(input_data)
    print(json.dumps(outline_and_report, indent=2))
