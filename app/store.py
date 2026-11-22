import copy
import threading
from datetime import datetime, timezone

from app.nutrition import analyze_ingredients


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_SEED = [
    {
        "id": "meal_101",
        "ownerId": "user-a",
        "title": "Chicken rice bowl",
        "mealType": "lunch",
        "eatenAt": "2026-11-17T12:30:00Z",
        "imagePath": "uploads/user-a/chicken-rice-bowl.jpg",
        "notes": "Post-workout lunch.",
        "ingredients": [
            {"name": "chicken breast", "grams": 150, "confidence": 0.94},
            {"name": "white rice", "grams": 200, "confidence": 0.9},
            {"name": "broccoli", "grams": 80, "confidence": 0.82},
        ],
    },
    {
        "id": "meal_102",
        "ownerId": "user-a",
        "title": "Oatmeal with banana",
        "mealType": "breakfast",
        "eatenAt": "2026-11-18T07:45:00Z",
        "imagePath": "uploads/user-a/oatmeal-banana.png",
        "notes": None,
        "ingredients": [
            {"name": "oats", "grams": 60, "confidence": 0.88},
            {"name": "banana", "grams": 100, "confidence": 0.95},
            {"name": "milk", "grams": 200, "confidence": 0.7},
        ],
    },
    {
        "id": "meal_103",
        "ownerId": "user-b",
        "title": "Salmon with potatoes",
        "mealType": "dinner",
        "eatenAt": "2026-11-17T19:10:00Z",
        "imagePath": "uploads/user-b/salmon-potatoes.jpg",
        "notes": None,
        "ingredients": [
            {"name": "salmon", "grams": 180, "confidence": 0.91},
            {"name": "potato", "grams": 250, "confidence": 0.86},
            {"name": "olive oil", "grams": 10, "confidence": 0.55},
        ],
    },
    {
        "id": "meal_104",
        "ownerId": "user-b",
        "title": "Greek salad",
        "mealType": "lunch",
        "eatenAt": "2026-11-18T13:00:00Z",
        "imagePath": "uploads/user-b/greek-salad.jpeg",
        "notes": "Restaurant portion.",
        "ingredients": [
            {"name": "tomato", "grams": 120, "confidence": 0.9},
            {"name": "cucumber", "grams": 100, "confidence": 0.88},
            {"name": "feta cheese", "grams": 50, "confidence": 0.8},
            {"name": "olive oil", "grams": 15, "confidence": 0.5},
        ],
    },
    {
        "id": "meal_105",
        "ownerId": "user-b",
        "title": "Blurry snack photo",
        "mealType": "snack",
        "eatenAt": "2026-11-18T16:20:00Z",
        "imagePath": "uploads/user-b/blurry-snack.jpg",
        "notes": "The AI could not recognise this meal.",
        "ingredients": [],
    },
]


def build_meal(meal_id: str, owner_id: str, fields: dict, created_at: str, updated_at: str) -> dict:
    """Assemble a full meal record and compute its nutrition from the ingredients."""
    ingredients, totals, status = analyze_ingredients(fields["ingredients"])
    return {
        "id": meal_id,
        "ownerId": owner_id,
        "title": fields["title"],
        "mealType": fields["mealType"],
        "eatenAt": fields["eatenAt"],
        "imagePath": fields["imagePath"],
        "notes": fields.get("notes"),
        "status": status,
        "ingredients": ingredients,
        "totals": totals,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }


class MealStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        """Reload the seed data (also what happens on every server restart)."""
        with self._lock:
            self._meals = {}
            seeded_at = "2026-11-18T18:00:00Z"
            for raw in _SEED:
                meal = build_meal(raw["id"], raw["ownerId"], raw, seeded_at, seeded_at)
                self._meals[meal["id"]] = meal
            self._next_id = 106

    def all(self) -> list[dict]:
        with self._lock:
            return [copy.deepcopy(m) for m in self._meals.values()]

    def get(self, meal_id: str) -> dict | None:
        with self._lock:
            meal = self._meals.get(meal_id)
            return copy.deepcopy(meal) if meal else None

    def find_duplicate(self, owner_id: str, title: str, eaten_at: str, exclude_id: str | None = None):
        """A meal with the same owner, title and time is treated as a duplicate upload."""
        with self._lock:
            for meal in self._meals.values():
                if (
                    meal["id"] != exclude_id
                    and meal["ownerId"] == owner_id
                    and meal["title"].lower() == title.lower()
                    and meal["eatenAt"] == eaten_at
                ):
                    return copy.deepcopy(meal)
        return None

    def create(self, owner_id: str, fields: dict) -> dict:
        with self._lock:
            meal_id = f"meal_{self._next_id}"
            self._next_id += 1
            now = utc_now_iso()
            meal = build_meal(meal_id, owner_id, fields, now, now)
            self._meals[meal_id] = meal
            return copy.deepcopy(meal)

    def replace(self, meal_id: str, fields: dict) -> dict:
        with self._lock:
            old = self._meals[meal_id]
            meal = build_meal(meal_id, old["ownerId"], fields, old["createdAt"], utc_now_iso())
            self._meals[meal_id] = meal
            return copy.deepcopy(meal)

    def delete(self, meal_id: str) -> None:
        with self._lock:
            del self._meals[meal_id]

    def count(self) -> int:
        with self._lock:
            return len(self._meals)


store = MealStore()
