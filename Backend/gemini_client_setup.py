from google import genai
from dotenv import load_dotenv
import os
import json
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
    
def call_llm_swot(input_data: Dict[str, Any]):
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

    response=client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_template,
        config={
            "response_mime_type":"application/json",
            "temperature": 0.2
        }
    )

    text=(response.text or "").strip()
    try:
        data=json.loads(text)
        return data
    except:
        raise ValueError("Incorrect output format by LLM. Raw output:\n",text)
    
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
    swot_and_report = call_llm_swot(input_data)
    print(json.dumps(swot_and_report, indent=2))