import os
from groq import Groq
from django.conf import settings

class NotesService:
    def __init__(self):
        # Provide standalone Groq LLM configuration decoupled from chatbot app
        self.api_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        self.model = getattr(settings, "GROQ_MODEL", "llama3-70b-8192")
        
        if not self.api_key:
            self.api_key = os.getenv("GROQ_API_KEY")
            
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set.")
            
        self.client = Groq(api_key=self.api_key)

    def generate_notes(self, query):
        search_context = ""
        image_url = None
        
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                # Top 3 text results for RAG Context
                text_results = list(ddgs.text(query, max_results=3))
                if text_results:
                    search_context = "--- LIVE WEB SEARCH CONTEXT ---\n"
                    for i, r in enumerate(text_results):
                        search_context += f"Source {i+1} ({r.get('title', 'Unknown')}): {r.get('body', '')}\n"
                    search_context += "-------------------------------\n"

                # 1 image result for top visual context
                image_results = list(ddgs.images(query, max_results=1))
                if image_results and len(image_results) > 0:
                    image_url = image_results[0].get('image')
        except Exception as e:
            search_context = f"(Live web search failed: {e})\n\n"

        prompt = f"""
        You are an advanced AI Python Study Assistant.
        User Query Topic: {query}
        
        {search_context}

        INSTRUCTIONS:
        Generate comprehensive, beautifully structured STUDY NOTES that help the user understand the requested topic EXCLUSIVELY in the context of Python.
        
        RULES:
        1. All code examples MUST be in Python.
        2. Reference standard Python libraries (e.g., collections, itertools) or popular Python frameworks where applicable.
        3. If the topic is a general CS concept (e.g., Linked Lists), show the Pythonic implementation.
        4. If the topic is completely unrelated to Python (e.g., Java specifically, CSS, or non-tech), explain that CobraTutor is specialized for Python and provide a brief Python-related alternative.
        5. DO NOT act conversational. DO NOT output conversational filler like "Here are the notes:". Just output raw markdown.
        
        Format the notes in Markdown using:
        - # Title for the topic
        - ## Core Definition (as it relates to Python)
        - ## Pythonic Implementation / Best Practices
        - ## Key Insights (synthesized from search results)
        - ## Real-World Python Use Cases
        """
        
        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.7,
            )
            response_text = completion.choices[0].message.content
            
            # Inject beautiful responsive Image block at the top if found
            if image_url:
                response_text = f"![{query} Banner Image]({image_url})\n***\n\n{response_text}"
                
            return response_text
        except Exception as e:
            return f"I'm having trouble compiling notes right now. ({e})"
