import sys, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from chatbot.services.recommendation_service import RecommendationService
rec = RecommendationService()

print(f"Total concepts: {len(rec.gkt.concepts)}")
for i, c in enumerate(rec.gkt.concepts):
    if "Python" in c or "python" in c.lower():
        mastery = rec.gkt.get_mastery("abcd@gmail.com", c)
        print(f"[{i}] {c} Mastery: {mastery}")
        
        state = rec.gkt.state.get("abcd@gmail.com", {})
        print(f"   Tutor: {state.get('tutor', [])[i]}")
        print(f"   Code:  {state.get('code', [])[i]}")
        print(f"   Debug: {state.get('debug', [])[i]}")

next_topic = rec.get_next_best_step("abcd@gmail.com", "Python Basics")
print(f"Next recommended topic: {next_topic}")
