# name: (kcal, protein g, carbohydrates g, fat g) per 100 g
NUTRITION_PER_100G = {
    "apple": (52, 0.3, 13.8, 0.2),
    "avocado": (160, 2.0, 8.5, 14.7),
    "banana": (89, 1.1, 22.8, 0.3),
    "beef": (250, 26.0, 0.0, 15.0),
    "bread": (247, 13.0, 41.0, 3.4),
    "broccoli": (34, 2.8, 6.6, 0.4),
    "cheddar cheese": (403, 24.9, 1.3, 33.1),
    "chicken breast": (165, 31.0, 0.0, 3.6),
    "cucumber": (15, 0.7, 3.6, 0.1),
    "egg": (155, 12.6, 1.1, 10.6),
    "feta cheese": (264, 14.2, 3.9, 21.3),
    "greek yogurt": (59, 10.2, 3.6, 0.4),
    "lentils": (116, 9.0, 20.1, 0.4),
    "lettuce": (15, 1.4, 2.9, 0.2),
    "milk": (61, 3.2, 4.8, 3.3),
    "oats": (389, 16.9, 66.3, 6.9),
    "olive oil": (884, 0.0, 0.0, 100.0),
    "pasta": (131, 5.0, 25.0, 1.1),
    "potato": (87, 1.9, 20.1, 0.1),
    "salmon": (208, 20.4, 0.0, 13.4),
    "tomato": (18, 0.9, 3.9, 0.2),
    "white rice": (130, 2.7, 28.2, 0.3),
}

SUPPORTED_INGREDIENTS = sorted(NUTRITION_PER_100G)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def is_known_ingredient(name: str) -> bool:
    return normalize_name(name) in NUTRITION_PER_100G


def ingredient_nutrition(name: str, grams: float) -> dict:
    kcal, protein, carbs, fat = NUTRITION_PER_100G[normalize_name(name)]
    factor = grams / 100
    return {
        "calories": round(kcal * factor, 1),
        "protein": round(protein * factor, 1),
        "carbs": round(carbs * factor, 1),
        "fat": round(fat * factor, 1),
    }


def analyze_ingredients(ingredients: list[dict]) -> tuple[list[dict], dict, str]:
    """Return (ingredients with nutrition, meal totals, status).

    An empty ingredient list means the AI could not recognise the meal, so the
    status is "unknown" and all totals are 0 (FR-05).
    """
    enriched = []
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for item in ingredients:
        name = normalize_name(item["name"])
        facts = ingredient_nutrition(name, item["grams"])
        enriched.append({"name": name, "grams": item["grams"], "confidence": item["confidence"], **facts})
        for key in totals:
            totals[key] += facts[key]
    totals = {key: round(value, 1) for key, value in totals.items()}
    status = "analyzed" if enriched else "unknown"
    return enriched, totals, status
