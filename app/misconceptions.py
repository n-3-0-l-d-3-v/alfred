MISCONCEPTIONS_DB = {
    "nested loops": {
        "issue": "High time complexity",
        "reason": "Iterating within another iteration often yields O(N^2) or worse performance.",
        "suggestion": "Consider using dictionaries or hash sets for O(1) lookups to flatten the loops."
    },
    "brute force search": {
        "issue": "Inefficient linear search",
        "reason": "Using an if-statement inside a loop to search for a value is slow for large datasets.",
        "suggestion": "Use the 'in' operator with a set/dict, or built-in functions like '.index()'."
    }
}

def detect_misconceptions(patterns: list) -> list:
    """
    Takes a list of detected patterns and maps them to a list of underlying
    misconceptions with detailed explanations and suggestions.
    """
    misconceptions_found = []
    
    for pattern in patterns:
        if pattern in MISCONCEPTIONS_DB:
            # Create a combined dictionary with the pattern name and its details
            misconception = {"pattern": pattern}
            misconception.update(MISCONCEPTIONS_DB[pattern])
            misconceptions_found.append(misconception)
            
    return misconceptions_found
