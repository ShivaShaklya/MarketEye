from .chat_store import add_turn, save_chat

STAGE_GUIDANCE = {
    "exploration and problem_framing": {
        "goal": "clarify the idea and the problem at a high level",
        "questions": [
            {
                "key": "problem_area",
                "prompt": "What kind of problem is this mainly about? (e.g., cost, access, convenience, speed, safety)"
            },
            {
                "key": "usage_context",
                "prompt": "In what situation does this problem usually show up? (daily use, work, travel, emergencies, etc.)"
            },
            {
                "key": "geolocation",
                "prompt": "Is this product needed more in any specific region or country?"
            },
        ]
    },

    "solution_design and solution_detailing": {
        "goal": "shape the solution and check basic feasibility",
        "questions": [
            {
                "key": "geolocation",
                "prompt": "Is this product needed more in any specific region or country?"
            },
            {
                "key": "budget_price_range",
                "prompt": "Do you have a rough price or budget in mind?"
            },
            {
                "key": "feature_priority",
                "prompt": "What matters more right now: cost, quality, speed, performance or simplicity?"
            },
            {
                "key": "distribution_preference",
                "prompt": "Who do you aim to sell the product to? (Businesses, Consumers, Both)"
            },
            {
                "key": "buyer_preference",
                "prompt": "How do you imagine people discovering or buying this? (online, offline, referrals, partnerships)"
            }
        ]
    },

    "market_validation_ready": {
        "goal": "prepare the idea for market validation and research",
        "questions": [
            {
                "key": "willingness_to_pay",
                "prompt": "Do you think users would easily pay for this, or would they need a strong reason to switch?"
            },
            {
                "key": "success_definition",
                "prompt": "What would success look like for you? (users, revenue, impact, adoption)"
            },
            {
                "key": "validation_method",
                "prompt": "How would you prefer to test this idea first? (pilot, prototype, survey, small launch)"
            }
        ]
    }
}

PREDEFINED_CONSTRAINT_KEYS = {
    "segment",
    "problem_area",
    "usage_context",
    "geolocation",
    "budget_price_range",
    "feature_priority",
    "distribution_preference",
    "channels",
    "willingness_to_pay",
    "success_definition",
    "validation_method"
}

FREE_FORM_KEYS = {
    "special_features"
}

NUMERIC_CLARIFIABLE = {
    "budget_price_range": {
        "prompt": "When you say '{value}', could you give a rough number or range?",
        "examples": "For example: ₹8,000–₹10,000 (rough estimate)"
    },
    "battery_life": {
        "prompt": "When you say '{value}', roughly how long do you mean?",
        "examples": "For example: 24 hours, 36 hours, 2 days"
    }
}

def is_quantifiable_feature(feature: str) -> bool:
    keywords = ["time", "duration", "life", "speed", "range", "capacity", "cost", "price"]
    f = feature.lower()
    return any(k in f for k in keywords)

def has_numeric_value(text: str) -> bool:
    return any(ch.isdigit() for ch in text)

def needs_numeric_clarification(value: str) -> bool:
    return not any(ch.isdigit() for ch in value)

def clarify_numeric_constraint(chat: dict, key: str, value: str):
    prompt = NUMERIC_CLARIFIABLE[key]["prompt"].format(value=value)
    print(f"\nYou mentioned '{value}'.")
    print(prompt)
    print(NUMERIC_CLARIFIABLE[key]["examples"])

    user_input = input("> ").strip()
    add_turn(chat, "user", user_input)

    if user_input:
        chat["constraints"][key] = user_input
        add_turn(chat, "assistant", f"Updated {key} to: {user_input}")
        save_chat(chat)

def clarify_special_features(chat: dict):
    features = chat["constraints"].get("special_features", [])
    clarified = []

    for feature in features:
        # ✅ Skip if already numeric
        if has_numeric_value(feature):
            clarified.append(feature)
            continue

        # ✅ Only clarify vague quantifiable features
        if is_quantifiable_feature(feature):
            print(f"\nYou mentioned '{feature}'.")
            print("Could you describe this more precisely?")
            print("For example: a number, range, or concrete expectation.")

            user_input = input("> ").strip()
            add_turn(chat, "user", user_input)

            if user_input:
                clarified.append(f"{feature} (~{user_input})")
            else:
                clarified.append(feature)
        else:
            clarified.append(feature)

    chat["constraints"]["special_features"] = clarified
    save_chat(chat)

def constraint_questionnaire(chat):
    ideation_stage=chat["idea_understanding"]["ideation_stage"]
    guidance=STAGE_GUIDANCE[ideation_stage]
    
    print(f"\nFor {ideation_stage} stage, our goal is to {guidance['goal']}\n")
    for q in guidance["questions"]:
        key=q["key"]

        if key in chat["constraints"]:
            value=chat["constraints"][key]

            if key in NUMERIC_CLARIFIABLE and isinstance(value,str) and needs_numeric_clarification(value):
                clarify_numeric_constraint(chat,key,value)
            continue

        print(q["prompt"])
        user_input=input("> ").strip()
        add_turn(chat, "user", user_input)

        if not user_input:
            continue

        chat.setdefault("constraints",{})
        chat["constraints"][key]=user_input
        add_turn(chat, "assistant", f"Noted {key}: {user_input}")
        save_chat(chat)

    if chat["constraints"].get("special_features"):
        clarify_special_features(chat)
    


