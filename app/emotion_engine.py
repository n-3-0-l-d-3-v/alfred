def get_emotion(analysis: dict, misconceptions: list) -> str:
    """
    Returns an emotional tone based on analysis results and misconceptions.
    Possible values: praise, mentor, sarcastic
    """
    if not misconceptions:
        return "praise"

    patterns = analysis.get("patterns", []) if analysis else []
    major_patterns = {"nested loops"}

    if any(p in major_patterns for p in patterns) or len(misconceptions) >= 2:
        return "sarcastic"

    return "mentor"
