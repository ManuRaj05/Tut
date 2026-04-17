from Code.models import UserMistake
import datetime

class MistakeService:
    def record_mistake(self, user_email, topic, mistake_description, source):
        """
        Logs a qualitative mistake for a user.
        """
        if not mistake_description or len(mistake_description) < 5:
            return

        mistake = UserMistake(
            user_email=user_email,
            topic=topic,
            mistake_description=mistake_description,
            source=source,
            created_at=datetime.datetime.utcnow()
        )
        mistake.save()
        print(f"Recorded mistake for {user_email} on {topic} ({source}): {mistake_description[:50]}...")

    def get_recent_mistakes(self, user_email, topic=None, limit=5):
        """
        Retrieves recent mistakes for context injection.
        """
        query = {"user_email": user_email}
        if topic:
            query["topic"] = topic
            
        return UserMistake.objects.filter(**query).order_by('-created_at')[:limit]

mistake_service = MistakeService()
