# import os
# import json
# import re

# SPECS_PATH="data/products/smartphones"

# FEATURE_SPEC_MAP = {
#     "display": ["screen_size", "resolution"],
#     "battery": ["battery_life"],
#     "performance": ["cpu", "ram", "gpu"],
#     "storage": ["storage"],
#     "design": ["weight", "color"],
#     "camera": ["camera"],
#     "speaker": ["audio"],
#     "thermals": ["cooling"],
# }

# def clean_text(text):
#     return text.lower().strip() if text else ""

# def extract_number(text):
#     if not text:
#         return None
#     match = re.search(r"\d+(\.\d+)?", text)
#     return float(match.group()) if match else None

# def clean_gpu(text):
#     if not text:
#         return None
#     match = re.search(r"(RTX\s*\d+|GTX\s*\d+)", text, re.IGNORECASE)
#     return match.group() if match else text

# def clean_cpu(text):
#     if not text:
#         return None
#     match = re.search(r"(i[3579])", text.lower())
#     return f"Intel {match.group().upper()}" if match else text


# def normalize_specs(raw):
#     specs = {}

#     # DISPLAY
#     if raw.get("standing_screen_display_size"):
#         specs["screen_size"] = raw["standing_screen_display_size"].lower()
#     if raw.get("screen_resolution"):
#         specs["resolution"] = raw["screen_resolution"].replace(" ", "")

#     # PERFORMANCE
#     if raw.get("processor"):
#         specs["cpu"] = raw["processor"]

#     if raw.get("ram"):
#         specs["ram"] = raw["ram"].replace(" ", "")

#     if raw.get("graphics_coprocessor"):
#         specs["gpu"] = clean_gpu(raw["graphics_coprocessor"])

#     # STORAGE
#     if raw.get("hard_drive"):
#         specs["storage"] = raw["hard_drive"]
#     elif raw.get("flash_memory_size"):
#         specs["storage"] = raw["flash_memory_size"]

#     # BATTERY
#     if raw.get("average_battery_life_in_hours"):
#         specs["battery_life"] = raw["average_battery_life_in_hours"]

#     # DESIGN
#     if raw.get("item_weight"):
#         specs["weight"] = raw["item_weight"]
#     if raw.get("color"):
#         specs["color"] = raw["color"]

#     return specs

# def load_specs(base_path):
#     specs_dict = {}

#     # for category in os.listdir(base_path):
#     #     cat_path = os.path.join(base_path, category)

#     for file in os.listdir(base_path): #category path
#         file_path = os.path.join(base_path, file) #category path

#         with open(file_path, "r", encoding="utf-8") as f:
#             data = json.load(f)

#         product=file.removesuffix(".json")
        
#         raw_specs=data.get("product_details",{})
#         if not product:
#             continue

#         normalized = normalize_specs(raw_specs)
#         specs_dict[product.strip().lower()] = normalized

#     return specs_dict

# def match_product(product, specs_dict):
#     product_key = clean_text(product)

#     # exact match
#     if product_key in specs_dict:
#         return specs_dict[product_key]

#     # partial match (fallback)
#     for key in specs_dict:
#         if product_key in key or key in product_key:
#             return specs_dict[key]

#     return {}

# def get_relevant_specs(product, feature, specs_dict):
#     product_specs = match_product(product, specs_dict)

#     keys = FEATURE_SPEC_MAP.get(feature, [])

#     extracted = []

#     for k in keys:
#         if k in product_specs:
#             extracted.append(f"{k.replace('_',' ')}: {product_specs[k]}")

#     return ". ".join(extracted)

##

import os
import json
import re

# -----------------------------
# FEATURE → SPEC MAP (SMARTPHONES)
# -----------------------------
FEATURE_SPEC_MAP = {
    "display": ["screen_size", "resolution"],
    "battery": ["battery", "battery_life"],
    "performance": ["ram", "storage", "chipset"],
    "storage": ["storage"],
    "design": ["weight", "color", "form_factor"],
    "camera": ["camera"],
    "speaker": ["audio"],
    "thermals": [],
}

# -----------------------------
# HELPERS
# -----------------------------
def clean_text(text):
    return text.lower().strip() if text else ""


def extract_number(text):
    if not text:
        return None
    match = re.search(r"\d+(\.\d+)?", text)
    return float(match.group()) if match else None


# -----------------------------
# NORMALIZE SMARTPHONE SPECS
# -----------------------------
def normalize_specs(raw):
    specs = {}

    # DISPLAY
    if raw.get("standing_screen_display_size"):
        specs["screen_size"] = raw["standing_screen_display_size"].lower()

    if raw.get("scanner_resolution"):
        specs["resolution"] = raw["scanner_resolution"].replace(" ", "")
    elif raw.get("screen_resolution"):
        specs["resolution"] = raw["screen_resolution"].replace(" ", "")

    # PERFORMANCE
    if raw.get("ram_memory_installed_size"):
        specs["ram"] = raw["ram_memory_installed_size"].replace(" ", "")
    elif raw.get("ram"):
        specs["ram"] = raw["ram"].replace(" ", "")

    if raw.get("processor"):
        specs["chipset"] = raw["processor"]

    # STORAGE
    if raw.get("memory_storage_capacity"):
        specs["storage"] = raw["memory_storage_capacity"]
    elif raw.get("flash_memory_size"):
        specs["storage"] = raw["flash_memory_size"]

    # BATTERY
    battery_raw = (
        raw.get("battery_capacity")
        or raw.get("battery_power_rating")
    )

    if battery_raw:
        specs["battery"] = battery_raw
        specs["battery_mah"] = extract_number(battery_raw)

    if raw.get("phone_talk_time"):
        specs["battery_life"] = raw["phone_talk_time"]

    # CAMERA
    if raw.get("other_camera_features"):
        specs["camera"] = raw["other_camera_features"]

    # DESIGN
    if raw.get("weight"):
        specs["weight"] = raw["weight"]
    elif raw.get("item_weight"):
        specs["weight"] = raw["item_weight"]

    if raw.get("color"):
        specs["color"] = raw["color"]

    if raw.get("form_factor"):
        specs["form_factor"] = raw["form_factor"]

    # SOFTWARE
    if raw.get("os"):
        specs["os"] = raw["os"]

    # FEATURES
    if raw.get("special_features"):
        specs["features"] = raw["special_features"]

    return specs


# -----------------------------
# LOAD ALL SPECS
# -----------------------------
def load_specs(base_path):
    specs_dict = {}

    for file in os.listdir(base_path):
        file_path = os.path.join(base_path, file)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        product = file.replace(".json", "")
        raw_specs = data.get("product_details", {})

        if not product:
            continue

        normalized = normalize_specs(raw_specs)
        specs_dict[clean_text(product)] = normalized

    return specs_dict


# -----------------------------
# MATCH PRODUCT
# -----------------------------
def match_product(product, specs_dict):
    product_key = clean_text(product)

    if product_key in specs_dict:
        return specs_dict[product_key]

    for key in specs_dict:
        if product_key in key or key in product_key:
            return specs_dict[key]

    return {}


# -----------------------------
# GET RELEVANT SPECS
# -----------------------------
def get_relevant_specs(product, feature, specs_dict):
    product_specs = match_product(product, specs_dict)

    keys = FEATURE_SPEC_MAP.get(feature, [])
    extracted = []

    for k in keys:
        if k in product_specs:
            extracted.append(f"{k.replace('_',' ')}: {product_specs[k]}")

    return ". ".join(extracted)