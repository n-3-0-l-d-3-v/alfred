from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

# Import our custom logic from analyzer.py
from app.analyzer import analyze_code

# Initialize the FastAPI application
app = FastAPI(title="Coding Mentor API")

# Define the expected JSON input structure
class CodeInput(BaseModel):
    code: str
    level: Literal["beginner", "intermediate"] = "beginner"

# Define a POST endpoint at /analyze
@app.post("/analyze")
def analyze_code_endpoint(input_data: CodeInput):
    """
    Receives code input, passes it to the AST analyzer, and returns the results.
    """
    # Pass the received 'code' and user 'level' to our analyze_code function
    result = analyze_code(input_data.code, input_data.level)
    
    # FastAPI automatically converts the dictionary to JSON format
    return result
