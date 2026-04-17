import sys, os
from dotenv import load_dotenv

# Load env variables from backend/.env if necessary or root .env
load_dotenv(".env")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

import django
django.setup()

from chatbot.services.recommendation_service import RecommendationService
rec = RecommendationService()

print(f"Total concepts loaded: {len(rec.gkt.concepts)}")
mastery = rec.gkt.get_mastery("abcd@gmail.com", "Python Basics")
print(f"Python Basics Mastery: {mastery}")

next_topic = rec.get_next_best_step("abcd@gmail.com", "Python Basics")
print(f"Next recommended topic: {next_topic}")
