
import math


class ScoringEngine:
    """
    Advanced Scoring Engine for CobraTutor.
    Implements a weighted aggregation of Understanding, Applying, and Analysis phases.
    """
    def __init__(self):
        # Weightage Configuration
        self.weights = {
            "understanding": 0.25, # Tutor Phase (Max 25)
            "applying": 0.35,      # Code Phase (Max 35)
            "analysis": 0.40       # Debug Phase (Max 40)
        }
        
    def calculate_tutor_score(self, questions_total, questions_correct):
        """
        Phase 1: Understanding (Tutor)
        Based on follow-up questions for subtopics.
        """
        print(questions_total,questions_correct,"Tutor")
        if questions_total == 0: return 0
        raw_score = (questions_correct / questions_total) * 100
        return raw_score

    def calculate_quiz_score(self, quiz_stats):
        """
        Phase 1 (Quiz): Direct Score Calculation.
        Input: { "correct": int, "total": int }
        Output: 0-100 Score
        """
        print(quiz_stats,"Quiz")
        correct = quiz_stats.get("correct", 0)
        total = quiz_stats.get("total", 0)
        if total == 0: return 0
        return (correct / total) * 100

    def calculate_code_score(self, question_results):
        """
        Phase 2: Applying (Coding) - Heavy Weightage
        Input: List of dicts for tasks (could be 1 or more).
        Each dict: {
            "difficulty": "easy"|"medium"|"hard",
            "passed": bool,
            "ai_usage": int,
            "test_failures": int
        }
        """
        print(question_results,"Code")
        if not question_results:
            return 0
            
        total_earned = 0
        total_possible = 0
        
        # Difficulty Base Points
        difficulty_weights = {"very easy": 100, "easy": 100, "medium": 100, "hard": 100} 
        
        for q in question_results:
            diff = q.get("difficulty", "medium")
            base_points = difficulty_weights.get(diff, 30)
            total_possible += base_points
            
            if not q.get("passed", False):
                continue # 0 points earned, but possible points added
                
            # Penalties
            # AI Usage: Negative, Max -50% of base points
            ai_penalty = min(q.get("ai_usage", 0) * 5, base_points * 0.5) 
            
            # Test Failures: -2 per fail, Max -30% of base points
            test_penalty = min(q.get("test_failures", 0) * 2, base_points * 0.3)
            
            q_score = max(0, base_points - ai_penalty - test_penalty)
            total_earned += q_score
            
        if total_possible == 0:
            return 0
            
        # Scale to 100
        return (total_earned / total_possible) * 100

    def calculate_debug_score(self, reasoning_level):
        """
        Phase 3: Analysis (Debugging) - Heavy Weightage
        Score based on reasoning capability.
        Input: 
        - str: "full" | "partial" | "none" (Legacy)
        - dict: { "attempts": int, "explanation_len": int } (New)
        """
        print(reasoning_level,"Debug",1234)
        # Handle New Payload
        if isinstance(reasoning_level, dict):
            attempts = reasoning_level.get("attempts", 1)
            explanation_len = reasoning_level.get("explanation_len", 0)
            
            # Attempt-Based Grading
            if attempts <= 1:
                base = 100
            elif attempts <= 3:
                base = 75
            else:
                base = 50
                
            # Explanation Quality Check
            if explanation_len < 10: # Too short (e.g., "fix")
                base -= 25
            
            return max(0, base)

        # Handle Legacy String
        if reasoning_level == "full":
            return 100
        elif reasoning_level == "partial":
            return 50
        else:
            return 0

    def aggregate_final_score(self, tutor_score, code_score, debug_score):
        """
        Aggregates individual components into the Final Mastery Score.
        """
        final_score = (
            (tutor_score * self.weights["understanding"]) +
            (code_score * self.weights["applying"]) + 
            (debug_score * self.weights["analysis"])
        )
        print(tutor_score,code_score,debug_score,"Final",self.weights)
        return round(final_score, 2)

    def determine_promotion(self, final_score):
        if final_score >= 80:
            return "PROMOTE"
        elif final_score >= 50:
            return "DEBUG" # Remediation path
        else:
            return "REMEDIATE"

