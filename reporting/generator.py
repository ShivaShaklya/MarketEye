from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape


class ReportGenerator:
    """Render fixed six-page PDF reports from structured MarketEye data."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = Path(template_dir or Path(__file__).parent)
        self.environment = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, payload: Dict[str, Any], output_pdf: Path) -> Path:
        output_pdf = Path(output_pdf)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)

        normalized = normalize_payload(payload)
        self._render_pdf_with_playwright(normalized, output_pdf)
        return output_pdf

    def write_html(self, payload: Dict[str, Any], output_html: Path) -> Path:
        output_html = Path(output_html)
        output_html.parent.mkdir(parents=True, exist_ok=True)

        normalized = normalize_payload(payload)
        html = self.render_html(normalized)
        output_html.write_text(html, encoding="utf-8")
        return output_html

    def render_html(self, payload: Dict[str, Any]) -> str:
        template = self.environment.get_template("template.html")
        return template.render(report=payload, now=datetime.utcnow().strftime("%d %b %Y"))

    def _render_pdf_with_playwright(self, payload: Dict[str, Any], output_pdf: Path) -> None:
        html = self.render_html(payload)
        sync_playwright = _load_playwright()

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "report.html"
            html_path.write_text(html, encoding="utf-8")

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
                page.pdf(
                    path=str(output_pdf),
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "0",
                        "right": "0",
                        "bottom": "0",
                        "left": "0",
                    },
                )
                browser.close()


def load_input_payload(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def transform_chat_to_report_payload(
    chat_payload: Dict[str, Any],
    asset_dir: str | Path | None = None,
    report_payload: Dict[str, Any] | None = None,
    report_dir: str | Path = "reports",
) -> Dict[str, Any]:
    del asset_dir  # Retained for compatibility with existing callers.

    report_payload = report_payload or _load_matching_report_payload(chat_payload, report_dir)
    analysis = _extract_analysis(report_payload, chat_payload)

    idea = chat_payload.get("idea_understanding", {})
    constraints = chat_payload.get("constraints", {})
    persona = _first_persona(chat_payload.get("customer_persona", {}))

    features_identified = _features_identified(chat_payload, analysis)
    constraints_noted = _constraints_noted(constraints)

    comparison_rows = _comparison_rows(analysis, report_payload, chat_payload)

    market_gap = analysis.get("market_gap_analysis", {})
    feasibility = analysis.get("feasibility_analysis", {})

    innovation_focus = _optional_list(
        analysis.get("innovation_focus_points")
        or report_payload.get("innovation_focus_points")
        or chat_payload.get("innovation_focus_points")
    )
    swot = _swot_items(
        analysis.get("swot_analysis")
        or analysis.get("swot")
        or analysis.get("SWOT")
        or report_payload.get("swot_analysis")
        or report_payload.get("swot")
        or report_payload.get("SWOT")
        or chat_payload.get("swot_analysis")
        or chat_payload.get("swot")
        or chat_payload.get("SWOT")
    )
    ending_statement = _optional_scalar(
        analysis.get("ending_statement")
        or analysis.get("EndStatement")
        or report_payload.get("ending_statement")
        or report_payload.get("EndStatement")
        or chat_payload.get("ending_statement")
        or chat_payload.get("EndStatement")
    )

    page1 = {
        "title": "Idea Snapshot",
        "raw_idea": _optional_scalar(chat_payload.get("idea_raw")),
        "domain": _optional_scalar(idea.get("domain")),
        "subdomain": _optional_scalar(idea.get("subdomain")),
        "one_line_description": _optional_scalar(idea.get("one_line_description")),
        "features_identified": features_identified,
        "constraints_noted": constraints_noted,
    }

    page2 = {
        "title": "Customer Persona",
        "name": _optional_scalar(persona.get("name")),
        "role_or_profile": _optional_scalar(persona.get("role_or_profile")),
        "demographic_details": _optional_list(persona.get("demographic_details")),
        "primary_need": _optional_scalar(persona.get("primary_need")),
        "buying_motivation": _optional_scalar(persona.get("buying_motivation")),
        "key_pain_points": _optional_list(persona.get("key_pain_points")),
        "constraints_sensitivity": _optional_dict_items(persona.get("constraints_sensitivity")),
        "adoption_friction": _optional_list(persona.get("adoption_friction")),
    }

    page3 = {
        "title": "Competition Analysis",
        "comparison_rows": comparison_rows,
    }

    page4 = {
        "title": "Market Gap Analysis",
        "existing_gaps": _optional_list(market_gap.get("existing_gaps"))[:3],
        "unmet_features": _optional_list(market_gap.get("unmet_features"))[:3],
        "opportunity_level": _optional_scalar(market_gap.get("opportunity_level")),
    }

    page5 = {
        "title": "Feasibility Analysis",
        "innovation_focus_points": innovation_focus,
        "is_feasible": _feasibility_status(feasibility.get("is_feasible")),
        "feasibility_question": "Is your idea feasible?",
        "reasoning": _optional_scalar(feasibility.get("reasoning")),
        "technical_challenges": _optional_list(feasibility.get("technical_challenges")),
        "cost_constraints": _optional_list(feasibility.get("cost_constraints")),
        "implementation_challenges": _optional_list(analysis.get("implementation_challenges")),
    }

    page6 = {
        "title": "SWOT & Final Statement",
        "swot": swot,
        "ending_statement": ending_statement,
    }

    return {
        "title": "MarketEye Project Report",
        "brand": "MarketEye",
        "author": _optional_scalar(chat_payload.get("user_id")),
        "date": _format_iso_date(chat_payload.get("updated_at")) or datetime.utcnow().strftime("%d %b %Y"),
        "meta": {
            "status": _optional_scalar(chat_payload.get("status")),
        },
        "pages": [page1, page2, page3, page4, page5, page6],
    }


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("title", "MarketEye Project Report")
    normalized.setdefault("brand", "MarketEye")
    normalized.setdefault("author", "")
    normalized.setdefault("date", datetime.utcnow().strftime("%d %b %Y"))
    normalized.setdefault("meta", {})

    pages: List[Dict[str, Any]] = []
    for index, page in enumerate(payload.get("pages", []), start=1):
        page_copy = dict(page)
        page_copy.setdefault("title", f"Page {index}")
        page_copy["page_number"] = index
        pages.append(page_copy)
    normalized["pages"] = pages
    return normalized


def _load_matching_report_payload(chat_payload: Dict[str, Any], report_dir: str | Path) -> Dict[str, Any]:
    user_id = chat_payload.get("user_id")
    chat_id = chat_payload.get("chat_id")
    if not user_id or not chat_id:
        return {}

    candidate = Path(report_dir) / f"{user_id}_{chat_id}_rag.json"
    if not candidate.exists():
        return {}
    return load_input_payload(candidate)


def _extract_analysis(report_payload: Dict[str, Any], chat_payload: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(report_payload.get("response"), dict):
        response = report_payload["response"]
        if isinstance(response.get("analysis"), dict):
            return response["analysis"]
        return response

    competitive_analysis = chat_payload.get("competitive_analysis")
    if isinstance(competitive_analysis, dict):
        if isinstance(competitive_analysis.get("analysis"), dict):
            return competitive_analysis["analysis"]
        return competitive_analysis
    return {}


def _first_persona(persona_bundle: Dict[str, Any]) -> Dict[str, Any]:
    personas = persona_bundle.get("personas")
    if isinstance(personas, list) and personas:
        first = personas[0]
        return first if isinstance(first, dict) else {}
    return {}


def _features_identified(chat_payload: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
    constraints = chat_payload.get("constraints", {})
    items: List[str] = []

    if constraints.get("feature_priority"):
        items.append(_clean_text(str(constraints["feature_priority"])))

    special_features = constraints.get("special_features")
    if isinstance(special_features, list):
        items.extend(_clean_text(str(item)) for item in special_features if _has_value(item))
    elif _has_value(special_features):
        items.append(_clean_text(str(special_features)))

    source_features = analysis.get("features_identified") or analysis.get("key_features")
    if isinstance(source_features, list):
        items.extend(_clean_text(str(item)) for item in source_features if _has_value(item))

    return _unique_items(items)


def _constraints_noted(constraints: Dict[str, Any]) -> List[str]:
    if not isinstance(constraints, dict) or not constraints:
        return []

    items = []
    for key, value in constraints.items():
        label = key.replace("_", " ").title()
        items.append(f"{label}: {_display_value(value)}")
    return items


def _comparison_rows(
    analysis: Dict[str, Any],
    report_payload: Dict[str, Any],
    chat_payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    top_competitors = analysis.get("top_competitors", [])
    if isinstance(top_competitors, list) and top_competitors:
        for item in top_competitors:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "name": _scalar_text(item.get("product_name")),
                    "price": _scalar_text(item.get("price")),
                    "key_features": _optional_list(item.get("key_features")),
                    "strengths": _optional_list(item.get("strengths")),
                    "weaknesses": _optional_list(item.get("weaknesses")),
                }
            )
        return rows

    retrieved_sources = []
    response = report_payload.get("response", {}) if isinstance(report_payload.get("response"), dict) else {}
    if isinstance(response.get("retrieved_products"), list):
        retrieved_sources.extend(response["retrieved_products"])

    competitive_analysis = chat_payload.get("competitive_analysis", {})
    if isinstance(competitive_analysis, dict) and isinstance(competitive_analysis.get("retrieved_products"), list):
        retrieved_sources.extend(competitive_analysis["retrieved_products"])

    for item in retrieved_sources:
        if not isinstance(item, dict):
            continue
        specs = item.get("specs", {}) if isinstance(item.get("specs"), dict) else {}
        rows.append(
            {
                "name": _scalar_text(item.get("product_name")),
                "price": _scalar_text(specs.get("price_rs") or specs.get("price") or item.get("price")),
                "key_features": [],
                "strengths": [],
                "weaknesses": [],
            }
        )

    return rows


def _feasibility_status(value: Any) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return ""


def _swot_items(value: Any) -> Dict[str, List[str]]:
    if not isinstance(value, dict):
        return {
            "Strengths": [],
            "Weaknesses": [],
            "Opportunities": [],
            "Threats": [],
        }

    return {
        "Strengths": _optional_list(value.get("strengths") or value.get("Strengths")),
        "Weaknesses": _optional_list(value.get("weaknesses") or value.get("Weaknesses")),
        "Opportunities": _optional_list(value.get("opportunities") or value.get("Opportunities")),
        "Threats": _optional_list(value.get("threats") or value.get("Threats")),
    }


def _optional_dict_items(value: Any) -> List[str]:
    if not isinstance(value, dict) or not value:
        return []
    return [f"{key.replace('_', ' ').title()}: {_display_value(item)}" for key, item in value.items()]


def _optional_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = [_clean_text(str(item)) for item in value if _has_value(item)]
        return items
    if _has_value(value):
        return [_clean_text(str(value))]
    return []


def _scalar_text(value: Any) -> str:
    if not _has_value(value):
        return ""
    return _clean_text(str(value))


def _optional_scalar(value: Any) -> str:
    return _scalar_text(value)


def _display_value(value: Any) -> str:
    if isinstance(value, list):
        cleaned = [_clean_text(str(item)) for item in value if _has_value(item)]
        return ", ".join(cleaned) if cleaned else ""
    if isinstance(value, dict):
        return "; ".join(
            f"{key}: {_display_value(item)}" for key, item in value.items() if _has_value(item)
        ) or ""
    return _scalar_text(value)


def _unique_items(items: List[str]) -> List[str]:
    unique: List[str] = []
    seen = set()
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _format_iso_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y")
    except ValueError:
        return _clean_text(value)


def _clean_text(value: str) -> str:
    replacements = {
        "â‚¹": "₹",
        "â€™": "'",
        "â€œ": "\"",
        "â€\x9d": "\"",
        "â€“": "-",
        "â€”": "-",
    }
    cleaned = value
    for src, dest in replacements.items():
        cleaned = cleaned.replace(src, dest)
    return _sentence_start_upper(cleaned.strip())


def _sentence_start_upper(value: str) -> str:
    for index, char in enumerate(value):
        if char.isalpha():
            return value[:index] + char.upper() + value[index + 1:]
    return value


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright is not installed. Install the Python package and browser runtime before generating PDFs."
        ) from exc
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright is installed, but the browser runtime is unavailable. "
            "Run 'python -m playwright install chromium' to install Chromium."
        ) from exc
    return sync_playwright
