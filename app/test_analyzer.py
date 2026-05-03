from fastapi.testclient import TestClient
from app.main import app

# Initialize the TestClient with our FastAPI app
client = TestClient(app)

def test_analyze_simple_loop_and_assignment():
    """Test a basic for loop and variable assignments."""
    code = "x = 10\nfor i in range(x):\n    print(i)"
    response = client.post("/analyze", json={"code": code})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["loops"] == 1
    # 'x' and 'i' should be tracked, but 'range' and 'print' should be ignored
    assert set(data["variables"]) == {"x", "i"}
    assert data["error"] is None
    assert data["patterns"] == []
    assert data["misconceptions"] == []

def test_analyze_comprehension():
    """Test a list comprehension loop and variables."""
    code = "squares = [s*s for s in range(5)]"
    response = client.post("/analyze", json={"code": code})
    
    assert response.status_code == 200
    data = response.json()
    assert data["loops"] == 1
    assert set(data["variables"]) == {"squares", "s"}
    assert data["patterns"] == []

def test_analyze_syntax_error():
    """Test invalid Python syntax handling."""
    # Missing colon at the end of the for loop
    code = "for i in range(5)"
    response = client.post("/analyze", json={"code": code})
    
    assert response.status_code == 200
    data = response.json()
    assert data["error"] is not None
    assert "Syntax error" in data["error"]

def test_analyze_empty_string():
    """Test processing an empty string."""
    response = client.post("/analyze", json={"code": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["loops"] == 0
    assert data["variables"] == []
    assert data["error"] is None

def test_analyze_nested_loop():
    """Test detection of nested loops."""
    code = "for i in range(5):\n    for j in range(5):\n        x = i * j"
    response = client.post("/analyze", json={"code": code})
    
    assert response.status_code == 200
    data = response.json()
    assert data["loops"] == 2
    assert "nested loops" in data["patterns"]
    assert any(m["pattern"] == "nested loops" for m in data["misconceptions"])

def test_analyze_brute_force_search():
    """Test detection of brute force search (if statement inside loop with break/return)."""
    code = "target = 5\nfor num in [1, 2, 3, 4, 5]:\n    if num == target:\n        print('Found!')\n        break"
    response = client.post("/analyze", json={"code": code})
    
    assert response.status_code == 200
    data = response.json()
    assert "brute force search" in data["patterns"]
    assert any(m["pattern"] == "brute force search" for m in data["misconceptions"])

def test_analyze_no_false_positive_brute_force():
    """Test that an if-statement without break/return is not flagged as brute force."""
    code = "for num in [1, 2, 3, 4, 5]:\n    if num % 2 == 0:\n        print(num)"
    response = client.post("/analyze", json={"code": code})
    
    assert response.status_code == 200
    data = response.json()
    assert "brute force search" not in data["patterns"]

def test_analyze_solution_engine():
    """Test Phase 3 AI solution generation and comparison inclusion."""
    code = "for i in range(10):\n    pass"
    response = client.post("/analyze", json={"code": code})
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert solutions are populated
    assert "brute_force" in data["solutions"]
    assert "optimized" in data["solutions"]
    
    # Assert proper structure exists inside the solutions
    assert "time_complexity" in data["solutions"]["optimized"]
    
    # Assert comparison was calculated
    assert data["comparison"]["best"] == "optimized"
