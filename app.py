from flask import Flask, render_template, request, jsonify, session
import json
import os
from functools import wraps

# Backend imports
try:
    from Backend.gemini_client_setup import call_llm
    from Backend.chat_store import create_chat, save_chat, load_chat, add_turn
    from Backend.query_processing import preprocess_query, idea_confirmation, get_constraints_from_query
    from Backend.report import create_persona, create_market_overview
    BACKEND_AVAILABLE = True
except ImportError as e:
    print(f"Backend modules not available: {e}")
    BACKEND_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# In-memory session storage for active chats (use Redis/DB in production)
active_chats = {}

# Analysis history data
analysis_history = [
    "Smart Water Bottle Analysis",
    "Eco-Friendly Packaging",
    "AI Fitness Tracker",
    "Wireless Earbuds Market",
    "Plant-Based Snacks"
]

@app.route('/')
def dashboard():
    return render_template('dashboard.html', analysis_history=analysis_history)

@app.route('/full-report')
def full_report():
    return render_template('full_report.html', analysis_history=analysis_history)

@app.route('/market-overview')
def market_overview():
    return render_template('market_overview.html', analysis_history=analysis_history)

@app.route('/competitive-analysis')
def competitive_analysis():
    return render_template('competitive_analysis.html', analysis_history=analysis_history)

@app.route('/analyze', methods=['POST'])
def analyze():
    """Main analysis endpoint - uses AI backend when available, falls back to mock data"""
    data = request.json
    prompt = data.get('prompt', '')
    analysis_type = data.get('type', 'full')
    
    if not prompt:
        return jsonify({'success': False, 'error': 'No prompt provided'}), 400
    
    if BACKEND_AVAILABLE:
        try:
            return jsonify(perform_ai_analysis(prompt, analysis_type))
        except Exception as e:
            print(f"AI analysis failed: {e}")
            # Fallback to mock data on error
            return jsonify(get_mock_analysis(prompt, analysis_type))
    else:
        return jsonify(get_mock_analysis(prompt, analysis_type))

def perform_ai_analysis(prompt: str, analysis_type: str) -> dict:
    """Perform actual AI-powered analysis using the backend modules"""
    user_id = session.get('user_id', 'anonymous')
    
    # Create a new chat session
    chat, chat_id = create_chat(user_id=user_id)
    chat["idea_raw"] = prompt
    add_turn(chat, "user", prompt)
    
    # Preprocess and analyze the query
    processed_query, confidence_score = preprocess_query(prompt)
    
    # Get idea understanding from LLM
    understanding = idea_confirmation(chat, processed_query, confidence_score)
    chat["idea_understanding"] = understanding
    chat["status"] = "ANALYZING"
    
    # Extract constraints from the query
    constraints = get_constraints_from_query(chat)
    
    # Generate personas and market overview for richer analysis
    persona_data = None
    market_data = None
    
    try:
        persona_data = create_persona(chat)
    except Exception as e:
        print(f"Persona generation failed: {e}")
    
    try:
        market_data = create_market_overview(chat)
    except Exception as e:
        print(f"Market overview generation failed: {e}")
    
    # Save the chat
    save_chat(chat)
    
    # Build the response based on analysis type
    analysis = build_analysis_response(
        understanding=understanding,
        constraints=constraints,
        persona=persona_data,
        market=market_data,
        confidence=confidence_score,
        analysis_type=analysis_type
    )
    
    return {
        'success': True,
        'chat_id': chat_id,
        'analysis': analysis
    }

def build_analysis_response(understanding: dict, constraints: dict, persona: dict, 
                           market: dict, confidence: float, analysis_type: str) -> dict:
    """Build a structured analysis response from AI outputs"""
    
    # Extract pain points from persona if available
    pain_points = []
    if persona and 'personas' in persona:
        for p in persona.get('personas', []):
            pain_points.extend(p.get('key_pain_points', []))
    
    # Extract market gaps from market overview
    market_gaps = []
    if market:
        market_gaps = market.get('major_risks', []) + market.get('target_market_characteristics', [])[:2]
    
    # Extract opportunities/trends
    opportunities = []
    if market:
        opportunities = market.get('key_trends', []) + market.get('demand_drivers', [])
    
    # Generate mock competitors (would be replaced with real competitive analysis)
    competitors = [
        {'name': 'Market Leader A', 'price': '$129', 'rating': '4.3/5', 'features': 18},
        {'name': 'Competitor B', 'price': '$99', 'rating': '4.1/5', 'features': 14},
        {'name': 'Competitor C', 'price': '$159', 'rating': '4.5/5', 'features': 22}
    ]
    
    # Determine market viability based on understanding
    stage = understanding.get('ideation_stage', 'exploration')
    if 'validation' in stage.lower():
        viability = 'High'
    elif 'solution' in stage.lower():
        viability = 'Medium-High'
    else:
        viability = 'Moderate'
    
    return {
        'product_concept': understanding.get('one_line_description', ''),
        'domain': understanding.get('domain', ''),
        'subdomain': understanding.get('subdomain', ''),
        'ideation_stage': understanding.get('ideation_stage', ''),
        'market_gaps': market_gaps[:5] if market_gaps else [
            'Market analysis in progress',
            'Additional data being gathered',
            'Competitive landscape being mapped'
        ],
        'pain_points': pain_points[:5] if pain_points else [
            'User research insights pending',
            'Customer feedback analysis ongoing'
        ],
        'competitors': competitors,
        'opportunities': opportunities[:5] if opportunities else [
            'Innovation potential identified',
            'Market entry feasibility confirmed'
        ],
        'market_viability': viability,
        'confidence_score': round(confidence, 2),
        'constraints': constraints,
        'market_definition': market.get('market_definition', '') if market else ''
    }

def get_mock_analysis(prompt: str, analysis_type: str) -> dict:
    """Return mock analysis data when AI backend is not available"""
    return {
        'success': True,
        'analysis': {
            'product_concept': prompt,
            'market_gaps': [
                'Limited integration with health apps',
                'Poor battery life in current solutions',
                'High price point barriers for entry-level users'
            ],
            'pain_points': [
                'Users struggle with complex setup processes',
                'Lack of personalized recommendations',
                'Inconsistent data tracking across devices'
            ],
            'competitors': [
                {'name': 'Product A', 'price': '$99', 'rating': '4.2/5', 'features': 15},
                {'name': 'Product B', 'price': '$149', 'rating': '4.5/5', 'features': 20},
                {'name': 'Product C', 'price': '$79', 'rating': '3.8/5', 'features': 12}
            ],
            'opportunities': [
                'Focus on seamless user experience',
                'Competitive pricing in $80-$120 range',
                'Enhanced mobile app integration',
                'AI-powered personalization features'
            ],
            'market_viability': 'High',
            'confidence_score': 0.87
        }
    }

# API endpoints for conversational flow
@app.route('/api/chat/start', methods=['POST'])
def start_chat():
    """Start a new analysis chat session"""
    if not BACKEND_AVAILABLE:
        return jsonify({'success': False, 'error': 'Backend not available'}), 503
    
    data = request.json
    user_id = data.get('user_id', 'anonymous')
    idea = data.get('idea', '')
    
    if not idea:
        return jsonify({'success': False, 'error': 'No idea provided'}), 400
    
    try:
        chat, chat_id = create_chat(user_id=user_id)
        chat["idea_raw"] = idea
        add_turn(chat, "user", idea)
        
        processed_query, confidence_score = preprocess_query(idea)
        understanding = idea_confirmation(chat, processed_query, confidence_score)
        
        chat["idea_understanding"] = understanding
        chat["status"] = "WAITING_IDEA_CONFIRMATION"
        save_chat(chat)
        
        # Store in active chats
        active_chats[chat_id] = chat
        
        return jsonify({
            'success': True,
            'chat_id': chat_id,
            'understanding': understanding,
            'confidence_score': confidence_score,
            'status': chat["status"]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat/<chat_id>/confirm', methods=['POST'])
def confirm_understanding(chat_id):
    """Confirm or edit the idea understanding"""
    if chat_id not in active_chats:
        return jsonify({'success': False, 'error': 'Chat not found'}), 404
    
    chat = active_chats[chat_id]
    data = request.json
    confirmed = data.get('confirmed', False)
    edits = data.get('edits', {})
    
    if confirmed:
        chat["status"] = "WAITING_CONSTRAINTS"
        constraints = get_constraints_from_query(chat)
        save_chat(chat)
        
        return jsonify({
            'success': True,
            'status': chat["status"],
            'extracted_constraints': constraints
        })
    else:
        # Apply edits to understanding
        for key, value in edits.items():
            if key in chat["idea_understanding"]:
                chat["idea_understanding"][key] = value
        save_chat(chat)
        
        return jsonify({
            'success': True,
            'understanding': chat["idea_understanding"]
        })

@app.route('/api/chat/<chat_id>/report', methods=['GET'])
def get_report(chat_id):
    """Generate and return the full analysis report"""
    if chat_id not in active_chats:
        return jsonify({'success': False, 'error': 'Chat not found'}), 404
    
    chat = active_chats[chat_id]
    
    try:
        persona = create_persona(chat)
        market = create_market_overview(chat)
        
        return jsonify({
            'success': True,
            'report': {
                'idea_understanding': chat.get('idea_understanding', {}),
                'constraints': chat.get('constraints', {}),
                'customer_persona': persona,
                'market_overview': market
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'backend_available': BACKEND_AVAILABLE
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
