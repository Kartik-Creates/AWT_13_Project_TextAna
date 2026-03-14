def analyze_text(text: str):
    
    tech_keywords = [
        "python",
        "javascript",
        "machine learning",
        "ai",
        "backend",
        "api",
        "database"
    ]

    text_lower = text.lower()

    for word in tech_keywords:
        if word in text_lower:
            return "Tech Content"

    return "Non-Tech Content"