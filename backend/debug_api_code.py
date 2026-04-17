import os
import sys
import django
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mongoengine.connection import get_connection, connect
try:
    get_connection()
except Exception:
    connect('cobra_db', host='localhost', port=27017)

from users.models import User
from Code.services.agent_service import process_user_query

def debug():
    print("Fetching generic user...")
    user = User.objects.first()
    if not user:
        print("No user found. Exiting.")
        return
        
    print(f"Using User: {user.email} (ID: {user.id})")
    print("Calling process_user_query...")
    try:
        # We need to simulate how CodeAgentView calls it:
        # CodeAgentView passed user = request.user.id
        result = process_user_query("Generate questions about Linked Lists", user.id)
        print("Result:", json.dumps(result, indent=2))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug()
