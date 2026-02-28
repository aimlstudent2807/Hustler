from typing import Any, Dict, Optional


def build_diet_prompt_payload(
    body_data: Dict[str, Any],
    medical_data: Dict[str, Any],
    preferences: Dict[str, Any],
    lifestyle_timing: Dict[str, Optional[str]],
    sleep_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Construct a clean JSON payload that combines body, medical, preferences,
    lifestyle timing, and sleep analysis to be sent to Gemini.
    """
    payload: Dict[str, Any] = {
        "body_profile": body_data,
        "medical_profile": medical_data,
        "diet_preferences": preferences,
        "lifestyle_timing": {
            "wake_time": lifestyle_timing.get("wake_time"),
            "breakfast_time": lifestyle_timing.get("breakfast_time"),
            "lunch_time": lifestyle_timing.get("lunch_time"),
            "snack_time": lifestyle_timing.get("snack_time"),
            "dinner_time": lifestyle_timing.get("dinner_time"),
            "sleep_time": lifestyle_timing.get("sleep_time"),
        },
        "sleep_analysis": {
            "sleep_hours": sleep_analysis.get("sleep_hours"),
            "sleep_status": sleep_analysis.get("sleep_status"),
        },
    }

    return payload

