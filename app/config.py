API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

PROJECT_NAME = "AI Food Analyzer"
PROJECT_TAGLINE = "Snap a photo of your meal, get calories and macros in seconds."
PROJECT_DESCRIPTION = (
    "AI Food Analyzer is a meal analysis and nutrition tracking system. A user uploads a "
    "photo of a meal, a vision-language model identifies the ingredients and estimates "
    "their portions in grams, and the backend calculates calories, protein, carbohydrates "
    "and fat for each ingredient and for the whole meal. Every analysis is saved to the "
    "user's meal history."
)
TARGET_USERS = [
    "Health-conscious people and dieters who want to log meals without weighing food "
    "or searching calorie tables.",
    "Fitness enthusiasts and athletes who need accurate macronutrient breakdowns and "
    "a history of what they ate.",
]

TEAM = [
    {
        "name": "Gulay Mehraliyeva",
        "studentId": "19925",
        "built": "Meal CRUD endpoints, request validation, mock data and nutrition calculation",
    },
    {
        "name": "Araz Valishov",
        "studentId": "17884",
        "built": "Project setup, error envelope, token authentication and role checks, HTML greeting page",
    },
]

ENDPOINTS = [
    ("GET", f"{API_PREFIX}/greeting", "This page: project info, team and endpoint list (HTML).", "Public"),
    ("GET", f"{API_PREFIX}/health", "Health check used by the watchdog script.", "Public"),
    ("GET", f"{API_PREFIX}/meals", "List meals (own meals; admin sees all). Supports paging and filters.", "Bearer token"),
    ("GET", f"{API_PREFIX}/meals/{{id}}", "Get one analyzed meal with ingredients and nutrition totals.", "Bearer token"),
    ("POST", f"{API_PREFIX}/meals", "Create a meal analysis; nutrition totals are calculated by the server.", "Bearer token"),
    ("PUT", f"{API_PREFIX}/meals/{{id}}", "Replace a meal (e.g. corrected ingredients) and recalculate totals.", "Bearer token"),
    ("DELETE", f"{API_PREFIX}/meals/{{id}}", "Delete a meal from the history.", "Bearer token"),
]
