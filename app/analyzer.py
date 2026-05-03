import ast
from app.misconceptions import detect_misconceptions

def analyze_code(code: str) -> dict:
    """
    Analyzes Python code to count loops, extract variable names,
    detect coding patterns, and map them to misconceptions.
    """
    # Define our updated response structure
    result = {
        "loops": 0,
        "variables": [],
        "patterns": [],
        "misconceptions": [],
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
        result["patterns"] = list(patterns)
        
        # Run misconception detection
        result["misconceptions"] = detect_misconceptions(result["patterns"])

    except SyntaxError as e:
        # If the code contains invalid Python syntax, record it as an error string
        result["error"] = f"Syntax error: {e}"

    return result
