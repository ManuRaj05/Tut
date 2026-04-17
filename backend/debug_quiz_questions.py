
import os
import sys
import django
from mongoengine import connect

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from quizzes.models import Question

def check_questions():
    print("Checking Question data integrity...")
    questions = Question.objects.all()
    count = 0
    issues = 0
    
    for q in questions:
        count += 1
        if q.correct_answer not in q.choices:
            print(f"ISSUE FOUND in Q {q.id}:")
            print(f"  Topic: {q.topic_name}")
            print(f"  Question: {q.question_text}")
            print(f"  Correct: '{q.correct_answer}'")
            print(f"  Choices: {q.choices}")
            issues += 1
            
        # Also check for "stripped" equality just in case
        clean_correct = q.correct_answer.strip().lower()
        clean_choices = [c.strip().lower() for c in q.choices]
        
        if clean_correct not in clean_choices:
             print(f"  (Also fails strict strip/lower check)")

    print(f"\nChecked {count} questions. Found {issues} issues.")

if __name__ == "__main__":
    # Assuming local mongo connection as per settings.py usually
    # But let's check how settings.py connects. 
    # Usually mongoengine connect is called in apps.py or settings.
    # We might need to manually connect if this script runs standalone.
    from mongoengine.connection import get_connection
    try:
        get_connection()
    except Exception:
        connect('cobra_db', host='localhost', port=27017)
        
    check_questions()
