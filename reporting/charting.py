from __future__ import annotations

from pathlib import Path
from textwrap import fill
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


ACCENT = "#16324f"
MUTED = "#94a3b8"
GRID = "#d9e2ec"
TEXT = "#1f2933"
BACKGROUND = "#f8fafc"


def _base_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
            "text.color": TEXT,
            "axes.facecolor": BACKGROUND,
            "figure.facecolor": "white",
        }
    )


def _wrap_labels(labels: List[str], width: int = 24) -> List[str]:
    return [fill(label.replace("_", " ").title(), width=width) for label in labels]


def build_chat_charts(chat_payload: Dict, output_dir: Path) -> List[Dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _base_style()

    charts: List[Dict[str, str]] = []
    overview = chat_payload.get("market_overview", {})
    constraints = chat_payload.get("constraints", {})
    personas = chat_payload.get("customer_persona", {}).get("personas", [])

    landscape_path = output_dir / "market_landscape.png"
    _build_market_landscape_chart(overview, landscape_path)
    charts.append(
        {
            "path": str(landscape_path),
            "caption": "Research landscape across characteristics, trends, demand drivers, risks, and cited sources.",
        }
    )

    if constraints:
        constraints_path = output_dir / "constraint_profile.png"
        _build_constraints_chart(constraints, constraints_path)
        charts.append(
            {
                "path": str(constraints_path),
                "caption": "Constraint profile based on the factors captured during the MarketEye discovery flow.",
            }
        )

    if personas:
        persona_path = output_dir / "persona_friction.png"
        _build_persona_chart(personas[0], persona_path)
        charts.append(
            {
                "path": str(persona_path),
                "caption": "Primary persona tension points highlighting need intensity, pain points, and adoption friction.",
            }
        )

    return charts


def _build_market_landscape_chart(overview: Dict, output_path: Path) -> None:
    labels = [
        "Target Characteristics",
        "Key Trends",
        "Demand Drivers",
        "Major Risks",
        "Information Sources",
    ]
    values = [
        len(overview.get("target_market_characteristics", [])),
        len(overview.get("key_trends", [])),
        len(overview.get("demand_drivers", [])),
        len(overview.get("major_risks", [])),
        len(overview.get("sources_of_information", [])),
    ]

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    bars = ax.barh(_wrap_labels(labels), values, color=[ACCENT, ACCENT, "#2f6f8f", "#8b1e3f", MUTED])
    ax.set_title("Market Research Coverage", fontsize=15, fontweight="bold", pad=18)
    ax.set_xlabel("Number of structured insights")
    ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, values):
        ax.text(value + 0.06, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontsize=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _build_constraints_chart(constraints: Dict, output_path: Path) -> None:
    keys = list(constraints.keys())
    labels = _wrap_labels(keys, width=18)
    values = [max(1, len(_constraint_value_text(constraints[key])) // 12) for key in keys]

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    bars = ax.bar(labels, values, color=ACCENT, width=0.62)
    ax.set_title("Constraint Depth Profile", fontsize=15, fontweight="bold", pad=16)
    ax.set_ylabel("Relative detail score")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)

    for tick in ax.get_xticklabels():
        tick.set_rotation(18)
        tick.set_ha("right")

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.05, str(value), ha="center", fontsize=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _build_persona_chart(persona: Dict, output_path: Path) -> None:
    labels = ["Primary Need", "Pain Points", "Motivators", "Friction"]
    values = [
        max(1, len(persona.get("primary_need", "")) // 36),
        len(persona.get("key_pain_points", [])),
        max(1, len(persona.get("buying_motivation", "")) // 42),
        len(persona.get("adoption_friction", [])),
    ]

    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    bars = ax.barh(labels, values, color=["#1f4e79", "#315b7c", "#4f6d7a", "#7c3f58"])
    ax.set_title("Primary Persona Signal Map", fontsize=15, fontweight="bold", pad=16)
    ax.set_xlabel("Signal strength")
    ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, values):
        ax.text(value + 0.08, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontsize=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _constraint_value_text(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
