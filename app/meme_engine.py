MEME_TEMPLATES = {
    "nested loops": {
        "mentor": "Two loops walk into a bar... consider a hash map.",
        "sarcastic": "Brace yourself, O(N^2) is coming."
    },
    "brute force search": {
        "mentor": "Checking every item works, but sets exist for a reason.",
        "sarcastic": "Found it! On page 999 of your loop."
    }
}

def generate_memes(patterns: list, emotion: str) -> list:
    """
    Returns a small set of meme snippets based on patterns and emotion.
    Keeps output minimal to avoid overuse.
    """
    if emotion == "praise" or not patterns:
        return []

    for pattern in patterns:
        template = MEME_TEMPLATES.get(pattern, {}).get(emotion)
        if template:
            return [{"pattern": pattern, "text": template}]

    return []
