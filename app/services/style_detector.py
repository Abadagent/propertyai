def detect_style(text: str):
    t = text.lower().strip()

    if "ассаламу" in t or "ассалаума" in t:
        return {
            "greeting_style": "respectful_kz",
            "tone_style": "respectful_kz",
            "emoji_level": "low",
        }

    if "добрый день" in t or "добрый вечер" in t:
        return {
            "greeting_style": "formal",
            "tone_style": "formal",
            "emoji_level": "none",
        }

    if "здравствуйте" in t:
        return {
            "greeting_style": "formal",
            "tone_style": "formal",
            "emoji_level": "low",
        }

    if "привет" in t or "салам" in t:
        return {
            "greeting_style": "friendly",
            "tone_style": "friendly",
            "emoji_level": "low",
        }

    return {
        "greeting_style": "neutral",
        "tone_style": "friendly",
        "emoji_level": "low",
    }