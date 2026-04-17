from .gkt_service import GKTService

class ContextService:
    def __init__(self):
        self.gkt = GKTService()

    def get_mastery_context(self, user_email):
        """
        Returns a string summary of user mastery for LLM prompts.
        """
        try:
            vector = self.gkt.get_mastery_vector(user_email)
            concepts = self.gkt.concepts
            
            mastered = []
            learning = []
            weak = []
            
            for i, score in enumerate(vector):
                concept = concepts[i]
                percent = int(score * 100)
                
                if score > 0.8:
                    mastered.append(f"{concept} ({percent}%)")
                elif score > 0.4:
                    learning.append(f"{concept} ({percent}%)")
                else:
                    weak.append(f"{concept} ({percent}%)")
            
            context = "USER MASTERY PROFILE:\n"
            if mastered:
                context += f"- Mastered (Strong): {', '.join(mastered)}\n"
            if learning:
                context += f"- In Progress (Developing): {', '.join(learning)}\n"
            if weak:
                context += f"- Weak/New (Focus Areas): {', '.join(weak)}\n"

            # ADD RECENT MISTAKES
            try:
                from .mistake_service import mistake_service
                mistakes = mistake_service.get_recent_mistakes(user_email, limit=5)
                if mistakes:
                    context += "\n⚠️ RECENT LEARNING GAPS / MISTAKES:\n"
                    for m in mistakes:
                        context += f"- {m.topic}: {m.mistake_description}\n"
                    context += "\nINSTRUCTION: If any of these topics appear in the current lesson, prioritize explaining them and providing targeted practice to fill these specific gaps.\n"
            except Exception as me:
                print(f"Error adding mistakes to context: {me}")
            
            return context
        except Exception as e:
            return f"Mastery data unavailable: {str(e)}"

context_service = ContextService()
