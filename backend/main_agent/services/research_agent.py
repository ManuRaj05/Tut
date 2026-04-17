from .notes_service import NotesService

class ResearchAgent:
    def __init__(self):
        self.notes_service = NotesService()

    def handle(self, message, chat_history):
        """
        RAG Study Notes Agent orchestrating DuckDuckGo.
        Delegates completely to the decoupled local Notes Service.
        """
        # We process the user's specific query for generating the knowledge artifact
        return self.notes_service.generate_notes(message)
