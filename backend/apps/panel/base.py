from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView


class PanelView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]


def person(user):
    return {
        "id": user.id,
        "name": user.first_name or user.telegram_username or user.username,
        "username": user.telegram_username,
        "telegram_id": user.telegram_id,
        "gender": user.gender,
    }


def hhmm(t):
    return t.strftime("%H:%M") if t else None
