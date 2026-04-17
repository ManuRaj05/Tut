import json
from chatbot.services.groq_service import GroqService
from .vector_router import VectorRouter

class RouterAgent:
    def __init__(self):
        self.groq = GroqService()
        self.vector_router = VectorRouter()

    def route(self, message):
        """
        Classifies the user's message into one of three categories:
        1. PLAN: User wants to learn a new topic.
        2. ACTION: User wants to practice, code, debug, or take a quiz.
        3. CHAT: User wants to ask a question or have something explained.

        Returns:
        {
            "route": "PLAN" | "ACTION" | "CHAT",
            "topic": "extracted topic or None"
        }
        """
        # Fast Path: (Removed to ensure high-precision topic extraction for all messages)
        pass
        
        prompt = f"""
        You are the Router for an AI Tutor.
        Classify the User Message into one of these intents:

        1. PLAN: User wants to LEARN a new topic from scratch, START a formal lesson, or mentions "teach me" without a specific technical query (e.g. "I want to learn Python", "Start BFS lesson").
        2. ACTION: User explicitly asks for a tool (e.g. "Give me a quiz", "I want to code", "Practice", "Debug").
        3. QUESTION: User asks a technical "What is...", "How does...", "Explain..." or requests notes/definitions (e.g. "What is indexing?", "How do loops work?"). 
           **CRITICAL**: If there's any technical substance or inquiry about a concept, choose QUESTION.
        4. CHAT: Short, non-technical interactions ONLY. Greetings ("Hi"), simple affirmations ("Yes", "Ok"), or casual feedback ("That was great").

        Also detect the LEARNING STYLE:
        - "comprehensive" (default): Standard deep dive.
        - "concise": User wants "quick", "fast", "summary".
        - "test_prep": User mentions "test tomorrow", "exam", "theory".
        - "practical_prep": User mentions "practicals", "lab", "code only".

        User Message: "{message}"

        Return strictly JSON:
        {{
            "route": "PLAN" | "ACTION" | "QUESTION" | "CHAT",
            "topic": "The extracted technical topic (e.g. 'Recursion') or null if none found",
            "style": "comprehensive" | "concise" | "test_prep" | "practical_prep",
            "is_relevant": true | false
        }}

        **RELEVANCY CRITERIA**:
        - `is_relevant: true`: If the message is about Python, Programming, Computer Science, Algorithms, Data Structures, or standard Greetings/affirmations.
        - `is_relevant: false`: If the message is about unrelated hobbies (cooking, sports, fashion), politics, general trivia not related to tech, or non-CS academic subjects.
        """
        
        try:
            response = self.groq.generate_content(prompt)
            print(f"DEBUG: Raw Router Response: '{response}'")
            
            # Robust JSON Extraction
            import re
            
            # 1. Remove <think> blocks if present
            clean_text = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
            
            # 2. Extract JSON from code blocks if present
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            # 3. If still not pure JSON, try finding first '{' and last '}'
            json_match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group()
                
            data = json.loads(clean_text)
            return data
        except Exception as e:
            print(f"Router Error: {e}")
            return {"route": "CHAT", "topic": None, "style": "comprehensive"} # Default fallback
