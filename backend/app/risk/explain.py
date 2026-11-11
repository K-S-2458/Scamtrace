"""Risk explanation formatting for SCAMTRACE AI."""
from typing import Any, Dict, List


def format_risk_explanation(risk_data: Dict[str, Any]) -> str:
    """Format the risk breakdown into human-readable explanatory text."""
    score = risk_data.get("final_score", 0.0)
    band = risk_data.get("risk_band", "low").upper()
    lines = [
        f"Case Risk Assessment: {band} (Score: {score:.2f} / 1.00)",
        risk_data.get("disclaimer", ""),
        "",
        "Key Contributing Factors:",
    ]

    for factor in risk_data.get("breakdown", []):
        ev_str = ", ".join(factor.get("evidence_ids", [])) or "None"
        lines.append(
            f"- {factor['factor_name']} [Weight: {factor['weight']:.2f}, "
            f"Contrib: +{factor['contribution']:.2f}]: {factor['description']} "
            f"(Supporting Evidence: [{ev_str}])"
        )

    return "\n".join(lines)

