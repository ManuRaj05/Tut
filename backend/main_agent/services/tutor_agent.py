from chatbot.services.groq_service import GroqService

class TutorAgent:
    def __init__(self):
        self.groq = GroqService()

    def handle(self, message, chat_history, topic=None, subtopic=None, user_email=None):
        """
        Pure conversational agent. No tools. Just explanations.
        """
        mastery_context = ""
        if user_email:
            from chatbot.services.context_service import context_service
            mastery_context = context_service.get_mastery_context(user_email)

        context = f"Topic: {topic}, Subtopic: {subtopic}" if topic and subtopic else ""
        prompt = f"""
        You are a friendly AI Tutor.
        Conversation History:
        {chat_history}

        Current Context: {context}
        USER MASTERY PROFILE:
        {mastery_context}

        User: {message}

        Provide a clear, concise explanation. Use analogies if helpful. 
        Adjust your explanation based on the User's Mastery Profile.
        Do NOT try to open tools or create plans. Just teach.
        """
        
        try:
            response = self.groq.generate_content(prompt)
            return response
        except Exception as e:
            return f"I'm having trouble thinking right now. ({e})"
