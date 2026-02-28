import json
import logging
from typing import Any, Dict, Optional

import google.generativeai as genai  # type: ignore[import]
from flask import current_app

logger = logging.getLogger(__name__)


def _get_client():
    """
    Return a configured Gemini client if an API key is present.

    In local/dev setups without GEMINI_API_KEY this returns None so that the
    caller can fall back to a deterministic, offline plan generator instead of
    crashing the request.
    """
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY is not configured; using local fallback diet plan.")
        return None
    genai.configure(api_key=api_key)
    # Model name can be swapped centrally here.
    return genai.GenerativeModel("gemini-1.5-pro")


def _build_local_fallback_plan(prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a simple, timing-aware diet plan without calling Gemini."""
    lifestyle = prompt_payload.get("lifestyle_timing", {}) or {}
    sleep = prompt_payload.get("sleep_analysis", {}) or {}
    prefs = prompt_payload.get("diet_preferences", {}) or {}

    diet_pref = (prefs.get("diet_preference") or "").strip().lower()
    regional = (prefs.get("regional_cuisine") or "").strip()

    is_veg = diet_pref in {"vegetarian", "vegan", "jain"}
    is_vegan = diet_pref == "vegan"
    is_jain = diet_pref == "jain"

    def meal_block(title: str, time_key: str, items: Any) -> Dict[str, Any]:
        return {
            "title": title,
            "scheduled_time": lifestyle.get(time_key),
            "summary": "Choose 1–2 options; keep portions moderate and protein‑anchored.",
            "items": items,
        }

    def _veg_protein_word() -> str:
        if is_vegan:
            return "tofu/soya chunks"
        return "paneer/curd"

    def _snack_dairy_word() -> str:
        if is_vegan:
            return "unsweetened soy/almond yogurt"
        return "curd/Greek yogurt"

    # Light regional hint (only for display text)
    regional_hint = f" ({regional})" if regional else ""

    meals = {
        "early_morning": meal_block(
            f"Early Morning{regional_hint}",
            "wake_time",
            [
                "Warm water + lemon OR jeera water (1 glass)",
                "Soaked almonds (4–6) OR 1 banana (if workout soon)",
            ],
        ),
        "breakfast": meal_block(
            f"Breakfast{regional_hint}",
            "breakfast_time",
            (
                [
                    f"Moong dal chilla (2) + mint chutney + { _snack_dairy_word() } (1/2 cup)",
                    "Vegetable poha (1 bowl) + sprouts (1/2 cup)",
                    "Oats upma (1 bowl) + peanuts (1 tbsp)",
                ]
                if is_veg
                else [
                    "Veg poha/upma (1 bowl) + boiled eggs (2)",
                    "Masala oats (1 bowl) + omelette (2 eggs)",
                    "Idli (3) + sambar (1 bowl) + egg bhurji (small bowl)",
                ]
            ),
        ),
        "mid_morning_snack": meal_block(
            "Mid‑morning Snack",
            "snack_time",
            [
                f"Fruit (apple/guava/orange) + { _snack_dairy_word() } (1/2 cup)",
                "Roasted chana (1 handful) + coconut water (optional)",
            ],
        ),
        "lunch": meal_block(
            f"Lunch{regional_hint}",
            "lunch_time",
            (
                [
                    "2 phulka/chapati + dal (1 bowl) + sabzi (1 bowl) + salad",
                    "Rice (1 cup) + rajma/chole (1 bowl) + salad",
                    f"Curd (1/2 cup) + { _veg_protein_word() } bhurji (small bowl) + sabzi",
                ]
                if is_veg
                else [
                    "2 phulka/chapati + dal (1 bowl) + sabzi (1 bowl) + salad",
                    "Rice (1 cup) + chicken curry (1 bowl) + salad",
                    "Fish/chicken (palm-size) + sabzi (1 bowl) + 1 roti",
                ]
            ),
        ),
        "evening_snack": meal_block(
            "Evening Snack",
            "snack_time",
            (
                [
                    "Sprouts chaat (1 bowl) OR makhana (2 cups)",
                    f"Paneer/tofu tikka (palm-size) OR { _snack_dairy_word() } bowl + seeds (1 tsp)",
                ]
                if is_veg
                else [
                    "Egg bhurji (2 eggs) OR chicken salad (small bowl)",
                    "Makhana (2 cups) + buttermilk (1 glass)",
                ]
            ),
        ),
        "dinner": meal_block(
            f"Dinner{regional_hint}",
            "dinner_time",
            (
                [
                    "Moong dal khichdi (1 bowl) + salad + pickle (small)",
                    f"Paneer/tofu + mixed veg stir-fry (1 bowl) + 1 roti",
                    "Dal + sabzi + 1–2 roti (lighter than lunch)",
                ]
                if is_veg
                else [
                    "Chicken/fish (palm-size) + sautéed veggies (1–2 bowls)",
                    "Egg curry (2 eggs) + salad + 1 roti",
                    "Dal + sabzi + 1 roti (light)",
                ]
            ),
        ),
    }

    dinner_feedback = (
        "Dinner timing looks reasonable against your sleep window."
        if lifestyle.get("dinner_time") and lifestyle.get("sleep_time")
        else "Set both dinner and sleep time to unlock precise feedback."
    )

    hydration_timing = [
        "One glass within 30 minutes of waking.",
        "Small sips between breakfast and lunch, avoiding chugging with meals.",
        "Water or herbal tea between lunch and dinner, tapering 1 hour before sleep.",
    ]

    return {
        "meta": {"source": "fallback"},
        "meals": meals,
        "hydration": {
            "summary": "Hydrate steadily across the day, focusing on your wake window rather than late-night intake.",
            "timing_suggestions": hydration_timing,
        },
        "lifestyle": {
            "sleep_hours": sleep.get("sleep_hours"),
            "sleep_status": sleep.get("sleep_status") or "unknown",
            "dinner_timing_feedback": dinner_feedback,
            "recommended_workout_window": "Aim for a consistent 30–45 minute window in the morning or early evening.",
        },
    }


def generate_diet_plan(prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Gemini to generate a structured diet plan with lifestyle timing.

    Returns a parsed JSON dictionary produced by the model.
    """
    system_instruction = (
        "You are SwasthyaSync, an AI nutrition coach. "
        "Use the provided JSON payload to create a structured Indian-context diet plan. "
        "Use specific Indian dish names (not generic phrases) and include approximate portions in each item. "
        "For each meal, return 2–4 options under items[] as 'Dish (portion) + add-on' style. "
        "Avoid repeating the phrase 'aligned with your routine' inside summaries. "
        "Strictly align meals with the user's actual meal times: "
        "breakfast at breakfast_time, lunch at lunch_time, snacks at snack_time, "
        "and dinner at dinner_time. Ensure dinner is scheduled at least 2–3 hours "
        "before sleep_time, and if the supplied dinner_time is too close to sleep_time, "
        "suggest a corrected timing and explain why. Distribute calories intelligently "
        "across the wake window based on wake_time and sleep_time. "
        "If sleep_status is 'insufficient', include concrete sleep hygiene advice in a "
        "Lifestyle section. Generate hydration guidance as specific timing suggestions "
        "between meals instead of generic advice. Respond ONLY with valid JSON matching "
        "this structure: {"
        '"meals": {'
        '"early_morning": {...},'
        '"breakfast": {...},'
        '"mid_morning_snack": {...},'
        '"lunch": {...},'
        '"evening_snack": {...},'
        '"dinner": {...}'
        "},"
        '"hydration": { "summary": str, "timing_suggestions": [str] },'
        '"lifestyle": {'
        '"sleep_hours": number | null,'
        '"sleep_status": str,'
        '"dinner_timing_feedback": str,'
        '"recommended_workout_window": str'
        "}"
        "}"
    )

    model = _get_client()
    if model is None:
        # Local deterministic fallback when no API key is configured.
        return _build_local_fallback_plan(prompt_payload)

    try:
        response = model.generate_content(
            [
                {"role": "system", "parts": [system_instruction]},
                {
                    "role": "user",
                    "parts": [
                        "Here is the combined user profile JSON for diet generation:\n",
                        json.dumps(prompt_payload),
                    ],
                },
            ]
        )
        text = response.text or "{}"
        parsed: Dict[str, Any] = json.loads(text)
        if isinstance(parsed, dict):
            parsed.setdefault("meta", {})
            if isinstance(parsed.get("meta"), dict):
                parsed["meta"].setdefault("source", "gemini")
        return parsed
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Gemini diet generation failed: %s", exc)
        # Fallback minimal safe structure
        return _build_local_fallback_plan(prompt_payload)


def analyze_meal_from_image(
    *,
    image_bytes: bytes,
    mime_type: str,
    meal_label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use Gemini (when available) to analyse a meal image and return nutrition.

    Returns a dict:
      {
        "dish_name": str | null,
        "metrics": {
          "calories": float | None,
          "protein": float | None,
          "carbs": float | None,
          "fats": float | None,
          "sugar": float | None,
          "fiber": float | None,
        },
        "summary": str,
        "guidance": str,
        "insights": {
          "balance_score": int,  # 0–100
          "flags": [str],
          "next_meal_suggestions": [str],
        },
        "meta": {"source": "gemini" | "fallback"},
      }
    """
    model = _get_client()
    if model is None:
        return _build_local_meal_analysis_fallback(meal_label=meal_label)

    image_part = {"mime_type": mime_type, "data": image_bytes}

    instruction = (
        "You are an expert nutritionist. Estimate nutrition for the meal image. "
        "Detect the most likely primary dish name in 3–6 words (e.g. 'Idli with sambar', 'Paneer butter masala with naan'). "
        "If the image is unclear, do your best conservative estimate and use a generic dish name (e.g. 'Mixed Indian thali'). "
        "Then estimate calories and macros. "
        "For 'next_meal_suggestions', return 3–5 concrete ideas in plain language, including example dishes and portions. "
        "Respond ONLY with valid JSON in this exact shape: {"
        '"dish_name": string | null,'
        '"metrics": {'
        '"calories": number | null,'
        '"protein": number | null,'
        '"carbs": number | null,'
        '"fats": number | null,'
        '"sugar": number | null,'
        '"fiber": number | null'
        "},"
        '"summary": string,'
        '"guidance": string,'
        '"insights": {'
        '"balance_score": number,'
        '"flags": [string],'
        '"next_meal_suggestions": [string]'
        "}"
        "}"
    )

    try:
        response = model.generate_content(
            [
                {"role": "system", "parts": [instruction]},
                {
                    "role": "user",
                    "parts": [
                        "Analyse this plate of food and estimate macros and calories.",
                        image_part,
                    ],
                },
            ]
        )
        text = response.text or "{}"
        parsed: Dict[str, Any] = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Unexpected JSON from Gemini meal analysis")

        parsed.setdefault("dish_name", None)
        parsed.setdefault("metrics", {})
        metrics = parsed["metrics"]
        # Normalise numeric fields
        for key in ["calories", "protein", "carbs", "fats", "sugar", "fiber"]:
            try:
                val = metrics.get(key)
                metrics[key] = float(val) if val is not None else None
            except (TypeError, ValueError, AttributeError):
                metrics[key] = None

        parsed.setdefault("summary", "")
        parsed.setdefault("guidance", "")
        parsed.setdefault("insights", {})
        insights = parsed["insights"]
        if not isinstance(insights, dict):
            insights = {}
        insights.setdefault("balance_score", 50)
        insights.setdefault("flags", [])
        insights.setdefault("next_meal_suggestions", [])
        parsed["insights"] = insights

        parsed.setdefault("meta", {})
        if isinstance(parsed["meta"], dict):
            parsed["meta"].setdefault("source", "gemini")
        else:
            parsed["meta"] = {"source": "gemini"}

        return parsed
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Gemini meal analysis failed: %s", exc)
        return _build_local_meal_analysis_fallback(meal_label=meal_label)


def _build_local_meal_analysis_fallback(
    meal_label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic offline meal analysis when Gemini is unavailable.

    Uses rough templates per meal type; numbers are conservative examples,
    not personalised estimates.
    """
    base = {
        "calories": 350.0,
        "protein": 15.0,
        "carbs": 45.0,
        "fats": 10.0,
        "sugar": 8.0,
        "fiber": 6.0,
    }

    label = (meal_label or "").lower()
    if label == "breakfast":
        base.update({"calories": 400.0, "protein": 18.0})
    elif label == "lunch":
        base.update({"calories": 550.0, "protein": 22.0})
    elif label == "dinner":
        base.update({"calories": 450.0, "protein": 20.0})
    elif label == "snack":
        base.update({"calories": 200.0, "protein": 8.0})

    summary = "Example balanced meal with moderate calories and reasonable protein for the selected meal type."
    guidance = (
        "Use this as a demo estimate. Once Gemini is connected, values will adapt to the actual photo. "
        "Aim for at least 20–30 g protein at main meals, plenty of vegetables, and mostly whole grains."
    )

    insights = {
        "balance_score": 72,
        "flags": ["Demo-only estimate (offline mode)"],
        "next_meal_suggestions": [
            "If this meal was light on protein, make the next one protein‑anchored: dal + sabzi + 1–2 phulka, or grilled paneer/tofu/chicken with salad.",
            "If this was a heavier meal, choose a lighter next plate: mostly vegetables + a small portion of whole grains (1 roti or 1/2 cup rice).",
            "Keep sugary drinks minimal; prefer water, buttermilk, unsweetened tea or coffee.",
            "If this was dinner, avoid additional heavy snacks afterwards and focus on hydration and sleep routine.",
        ],
    }

    return {
        "dish_name": None,
        "metrics": base,
        "summary": summary,
        "guidance": guidance,
        "insights": insights,
        "meta": {"source": "fallback"},
    }


