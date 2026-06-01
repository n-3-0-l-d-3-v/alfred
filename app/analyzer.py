import ast
from app.misconceptions import detect_misconceptions
from app.solution_engine import generate_solutions, compare_solutions
from app.teaching_engine import generate_teaching
from app.emotion_engine import get_emotion
from app.meme_engine import generate_memes

def analyze_code(code: str, level: str = "beginner") -> dict:
    """
    Analyzes Python code to count loops, extract variable names,
    detect coding patterns, map them to misconceptions, and
    generate/compare alternative solutions.
    """
    # Define our updated response structure
    result = {
        "loops": 0,
        "variables": [],
        "patterns": [],
        "misconceptions": [],
        "solutions": {},
        "comparison": {},
        "teaching": {},
        "emotion": None,
        "memes": [],
        "error": None
    }

    try:
        # Parse the code into an Abstract Syntax Tree (AST)
        tree = ast.parse(code)
        
        # Use a set to avoid duplicate variable names
        variables = set()
        patterns = set()

        # Walk through all the nodes in the tree
        for node in ast.walk(tree):
            # Detect loops (for, while, comprehensions)
            if isinstance(node, (ast.For, ast.While, ast.AsyncFor, ast.comprehension)):
                result["loops"] += 1
                
                # If this is a standard loop node (has a body), check its contents
                if hasattr(node, 'body'):
                    for child in node.body:
                        # Walk the children to detect nested loop or brute force search (if statements inside loop)
                        for subnode in ast.walk(child):
                            if isinstance(subnode, (ast.For, ast.While, ast.AsyncFor, ast.comprehension)):
                                patterns.add("nested loops")
                            elif isinstance(subnode, ast.If):
                                # Only flag if the if-statement contains a 'break' or 'return'
                                for if_child in ast.walk(subnode):
                                    if isinstance(if_child, (ast.Break, ast.Return)):
                                        patterns.add("brute force search")
                                        break
            
            # Detect variables being assigned/stored
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    variables.add(node.id)
            
            # Detect function arguments as variables
            elif isinstance(node, ast.arg):
                variables.add(node.arg)

        # Convert the sets back to lists for JSON serialization
        result["variables"] = list(variables)
        
        # Run Phase 3: AI Solution Generation and Comparison
        result["solutions"] = generate_solutions(code)
        result["comparison"] = compare_solutions(result["solutions"])
        result["patterns"] = list(patterns)
        
        # Run misconception detection
        result["misconceptions"] = detect_misconceptions(result["patterns"])

        # Run Phase 4: Adaptive Teaching
        result["teaching"] = generate_teaching(result["misconceptions"], result["solutions"], level)

        # Run Phase 5: Emotion + Meme Engine
        result["emotion"] = get_emotion(result, result["misconceptions"])
        result["memes"] = generate_memes(result["patterns"], result["emotion"])

    except SyntaxError as e:
        # If the code contains invalid Python syntax, record it as an error string
        result["error"] = f"Syntax error: {e}"

    return result
