from chatbot.services.groq_service import GroqService

class PlannerAgent:
    def __init__(self):
        self.groq = GroqService()

    def create_plan(self, topic, style="comprehensive"):
        """
        Generates a learning plan based on the requested style.
        """
        prompt = f"""
        Create a learning plan for Python topic: "{topic}".
        Style context: "{style}"

        Styles:
        - "comprehensive": Standard 3-step flow (Theory -> Code -> Debug).
        - "concise": Teach Content -> Practice Code.
        - "test_prep": Teach Content (Theory + Examples) ONLY. No coding. Quick revision.
        - "practical_prep": Practice Code ONLY. One consolidated coding challenge.
        action can be["tutor" for teach_content,"debugger" for debug_code,"code" for practice_code,"dashboard" for dashboard]
        Return ONLY a JSON list of steps. No other text.
        
        Examples:
        [Comprehensive] -> [{{"step": "teach_content", "topic": "{topic} Theory & Examples", action="tutor"}}, {{"step": "practice_code", "topic": "{topic} Challenge", action="code"}}, {{"step": "practice_debug", "topic": "{topic} Debugging", action="debugger"}}]
        [Test Prep] -> [{{"step": "teach_content", "topic": "{topic} Theory & Examples", action="tutor"}}]
        [Practical] -> [{{"step": "practice_code", "topic": "{topic} Challenge", action="code"}}]
        
        Format:
        [
            {{"step": "teach_content", "topic": "...",action="..."}},
            ...
        ]
        """
        
        try:
            plan_json = self.groq.generate_content(prompt)
            print(f"DEBUG: Raw Plan Response: '{plan_json}'")
            
            import re
            
            # 1. Remove <think> blocks
            clean_text = re.sub(r"<think>.*?</think>", "", plan_json, flags=re.DOTALL).strip()
            
            # 2. Extract JSON from code blocks
            if "```json" in clean_text:
                 clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                 clean_text = clean_text.split("```")[1].split("```")[0].strip()
                 
            # 3. Last resort: regex find list brackets
            json_match = re.search(r"\[.*\]", clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group()
                 
            return clean_text
        except Exception as e:
            print(f"Plan Gen Error: {e}")
            return "[]"
