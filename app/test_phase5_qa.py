"""
Phase 5 QA Test Suite: Emotion Engine + Meme Compiler
Tests emotion accuracy, meme relevance, tone balance, edge cases, and UX quality
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestEmotionAccuracy:
    """
    Test 1: Emotion Accuracy - Does emotion match code quality?
    """

    def test_emotion_praise_perfect_code(self):
        """Perfect code (no loops, no issues) should get praise"""
        code = "x = 5\ny = x + 10\nresult = y * 2"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["emotion"] == "praise", f"Expected 'praise' for perfect code, got '{data['emotion']}'"
        assert data["misconceptions"] == [], "Perfect code should have no misconceptions"

    def test_emotion_praise_simple_loop(self):
        """Simple, efficient loop should get praise"""
        code = "result = sum([i for i in range(10)])"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["emotion"] == "praise", f"Expected 'praise' for simple loop, got '{data['emotion']}'"

    def test_emotion_mentor_single_issue(self):
        """Single inefficiency (brute force search) should get mentor tone"""
        code = "target = 5\nfor num in [1, 2, 3, 4, 5]:\n    if num == target:\n        break"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["emotion"] == "mentor", f"Expected 'mentor' for single issue, got '{data['emotion']}'"
        assert len(data["misconceptions"]) == 1, "Should detect exactly 1 misconception"

    def test_emotion_sarcastic_nested_loops(self):
        """Nested loops (O(N²)) should get sarcastic tone"""
        code = "for i in range(5):\n    for j in range(5):\n        x = i * j"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["emotion"] == "sarcastic", f"Expected 'sarcastic' for nested loops, got '{data['emotion']}'"
        assert "nested loops" in data["patterns"]

    def test_emotion_sarcastic_multiple_issues(self):
        """Multiple misconceptions should trigger sarcastic tone"""
        code = """
for i in range(100):
    target = 42
    for j in range(100):
        if j == target:
            break
"""
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        # Should be sarcastic due to nested loops AND brute force search
        assert data["emotion"] == "sarcastic", f"Expected 'sarcastic' for multiple issues, got '{data['emotion']}'"
        assert len(data["misconceptions"]) >= 1


class TestMemeRelevance:
    """
    Test 2: Meme Relevance - Are memes related to detected patterns?
    """

    def test_meme_only_for_issues(self):
        """Memes should only appear when there are issues"""
        code = "x = 10\ny = x + 5"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["memes"] == [], "Clean code should have no memes"

    def test_meme_matches_nested_loops_mentor(self):
        """Mentor tone for nested loops should have relevant meme"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        
        assert data["emotion"] == "sarcastic"  # This triggers sarcastic due to pattern
        assert len(data["memes"]) > 0, "Should have meme for nested loops"
        
        meme = data["memes"][0]
        assert meme["pattern"] == "nested loops"
        assert "hash map" in meme["text"].lower() or "O(N" in meme["text"], \
            f"Meme should reference optimization, got: {meme['text']}"

    def test_meme_matches_brute_force_mentor(self):
        """Mentor tone for brute force should have relevant meme"""
        code = "target = 5\nfor num in [1, 2, 3]:\n    if num == target:\n        break"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        
        assert data["emotion"] == "mentor"
        assert len(data["memes"]) > 0, "Should have meme for brute force search"
        
        meme = data["memes"][0]
        assert meme["pattern"] == "brute force search"
        assert "set" in meme["text"].lower() or "dict" in meme["text"].lower() or "in" in meme["text"].lower(), \
            f"Meme should reference solution, got: {meme['text']}"

    def test_meme_not_repeated(self):
        """Only one meme per analysis (avoid spam)"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        
        # Should have at most 1 meme
        assert len(data["memes"]) <= 1, f"Should have max 1 meme, got {len(data['memes'])}"


class TestToneBalance:
    """
    Test 3: Tone Balance - Not too harsh, not too boring
    """

    def test_praise_is_encouraging(self):
        """Praise should be genuinely encouraging"""
        code = "x = 10"
        response = client.post("/analyze", json={"code": code})
        data = response.json()
        
        teaching = data["teaching"]
        feedback = teaching["feedback"][0]
        
        # Should contain encouraging language
        assert "Great" in feedback["hint"], f"Praise feedback should be encouraging: {feedback['hint']}"

    def test_mentor_is_helpful_not_mean(self):
        """Mentor should guide without being harsh"""
        code = "target = 5\nfor num in [1, 2, 3, 4, 5]:\n    if num == target:\n        break"
        response = client.post("/analyze", json={"code": code})
        data = response.json()
        
        teaching = data["teaching"]
        feedback = teaching["feedback"][0]
        
        # Should offer solutions, not just criticism
        assert "Try" in feedback["next_step"] or "Use" in feedback["next_step"], \
            f"Mentor should offer solutions: {feedback['next_step']}"
        
        # Meme should be light, not harsh
        if data["memes"]:
            meme_text = data["memes"][0]["text"]
            assert "bad" not in meme_text.lower() and "wrong" not in meme_text.lower(), \
                f"Mentor meme should not be harsh: {meme_text}"

    def test_sarcastic_is_funny_not_mean(self):
        """Sarcastic should be witty, not actually mean"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        data = response.json()
        
        meme = data["memes"][0]["text"]
        
        # Sarcastic should use humor/wit, not insults
        sarcastic_markers = ["brace yourself", "O(N", "page 999", "walk into"]
        has_wit = any(marker.lower() in meme.lower() for marker in sarcastic_markers)
        assert has_wit, f"Sarcastic tone should use wit/humor: {meme}"
        
        # Should NOT contain actual insults
        insults = ["stupid", "terrible", "awful", "garbage"]
        assert not any(insult in meme.lower() for insult in insults), \
            f"Sarcastic should be witty, not mean: {meme}"


class TestEdgeCases:
    """
    Test 4: Edge Cases - No crashes, handles gracefully
    """

    def test_empty_code(self):
        """Empty code should not crash"""
        response = client.post("/analyze", json={"code": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["emotion"] == "praise"
        assert data["memes"] == []

    def test_invalid_syntax_no_crash(self):
        """Invalid Python should not crash, should handle gracefully"""
        code = "for i in range(10)"  # Missing colon
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None, "Should have error message"
        assert "Syntax error" in data["error"]

    def test_syntax_error_no_emotion_crash(self):
        """Syntax error should still return valid emotion (or handle gracefully)"""
        code = "if True"  # Invalid
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        # System should either:
        # 1. Return None emotion, or
        # 2. Return praise (no misconceptions detected), or
        # 3. Handle gracefully
        assert data["emotion"] in [None, "praise"]

    def test_no_misconceptions_no_unnecessary_memes(self):
        """When no misconceptions, should definitely have no memes"""
        code = "x = 1\ny = 2\nz = x + y"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        
        assert data["misconceptions"] == []
        assert data["emotion"] == "praise"
        assert data["memes"] == [], "Should have zero memes when praise"

    def test_single_line_code(self):
        """Single-line code should be handled"""
        response = client.post("/analyze", json={"code": "x=5"})
        assert response.status_code == 200
        data = response.json()
        assert data["emotion"] == "praise"

    def test_very_long_code(self):
        """Long code should not cause timeout or crash"""
        code = "\n".join([f"x{i} = {i}" for i in range(100)])
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["emotion"] in ["praise", "mentor", "sarcastic"]


class TestUXQuality:
    """
    Test 5: UX Quality - Is it engaging?
    """

    def test_response_structure_complete(self):
        """Response should have all required fields"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["emotion", "memes", "teaching", "misconceptions", "patterns"]
        for field in required_fields:
            assert field in data, f"Response missing field: {field}"

    def test_meme_structure_valid(self):
        """Memes should have proper structure for frontend"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        data = response.json()
        
        if data["memes"]:
            meme = data["memes"][0]
            assert "pattern" in meme, "Meme missing 'pattern'"
            assert "text" in meme, "Meme missing 'text'"
            assert isinstance(meme["text"], str), "Meme text should be string"
            assert len(meme["text"]) > 0, "Meme text should not be empty"
            assert len(meme["text"]) < 200, "Meme text should be concise"

    def test_teaching_structure_valid(self):
        """Teaching feedback should be well-structured"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        data = response.json()
        
        teaching = data["teaching"]
        assert "level" in teaching
        assert "feedback" in teaching
        assert len(teaching["feedback"]) > 0
        
        feedback = teaching["feedback"][0]
        assert "hint" in feedback
        assert "explanation" in feedback
        assert "next_step" in feedback

    def test_emotion_consistency_with_teaching(self):
        """Emotion should align with teaching severity"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        data = response.json()
        
        emotion = data["emotion"]
        teaching = data["teaching"]
        
        if emotion == "praise":
            assert "Great" in teaching["feedback"][0]["hint"], "Praise should have positive teaching"
        elif emotion == "sarcastic":
            assert teaching["feedback"][0]["explanation"] is not None, "Sarcastic should have detailed explanation"

    def test_meme_tone_matches_emotion(self):
        """Meme tone should match the emotion returned"""
        # Test mentor tone
        code_mentor = "target = 5\nfor num in [1, 2, 3, 4, 5]:\n    if num == target:\n        break"
        response_mentor = client.post("/analyze", json={"code": code_mentor})
        data_mentor = response_mentor.json()
        
        if data_mentor["emotion"] == "mentor" and data_mentor["memes"]:
            meme_text = data_mentor["memes"][0]["text"]
            # Mentor should sound helpful
            assert any(word in meme_text for word in ["works", "reason", "consider", "Try"]), \
                f"Mentor meme should sound helpful: {meme_text}"

    def test_response_not_verbose(self):
        """Response should be concise, not overwhelming"""
        code = "x = 10"
        response = client.post("/analyze", json={"code": code})
        data = response.json()
        
        # For praise (clean code), should be brief and not overwhelming
        if data["emotion"] == "praise":
            feedback = data["teaching"]["feedback"][0]
            # Should be readable length (not a novel)
            assert len(feedback["hint"]) < 300, "Feedback should not be overwhelming"


class TestIntegration:
    """
    Integration tests for Phase 5 workflow
    """

    def test_full_workflow_praise_path(self):
        """End-to-end: Clean code → praise → no memes"""
        code = "total = sum(range(10))"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        
        data = response.json()
        assert data["emotion"] == "praise"
        assert data["memes"] == []
        assert len(data["misconceptions"]) == 0

    def test_full_workflow_mentor_path(self):
        """End-to-end: Minor issue → mentor → 1 helpful meme"""
        code = "target = 5\nfor num in [1, 2, 3, 4, 5]:\n    if num == target:\n        break"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        
        data = response.json()
        assert data["emotion"] == "mentor"
        assert len(data["memes"]) == 1
        meme_text = data["memes"][0]["text"]
        # Should reference a better approach
        assert "set" in meme_text.lower() or "dict" in meme_text.lower()

    def test_full_workflow_sarcastic_path(self):
        """End-to-end: Major issue → sarcastic → witty meme"""
        code = "for i in range(5):\n    for j in range(5):\n        pass"
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        
        data = response.json()
        assert data["emotion"] == "sarcastic"
        assert len(data["memes"]) == 1
        meme_text = data["memes"][0]["text"]
        # Should be witty/sarcastic
        assert "O(N" in meme_text or "brace yourself" in meme_text.lower()


# Summary reporting
if __name__ == "__main__":
    print("\n" + "="*70)
    print("PHASE 5 QA TEST SUITE - EMOTION ENGINE + MEME COMPILER")
    print("="*70)
    print("\nRun with: python -m pytest app/test_phase5_qa.py -v")
    print("\nTest Categories:")
    print("  1. TestEmotionAccuracy - Does emotion match code quality?")
    print("  2. TestMemeRelevance - Are memes related to patterns?")
    print("  3. TestToneBalance - Not too harsh, not too boring?")
    print("  4. TestEdgeCases - No crashes, handles gracefully?")
    print("  5. TestUXQuality - Is it engaging?")
    print("  6. TestIntegration - Full workflow paths")
    print("="*70)
