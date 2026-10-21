from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView


class PanelView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]


def person(user):
    return {
        "id": user.id,
        "name": user.display_name,
        "username": user.telegram_username,
        "region": user.get_region_display() if user.region else "",
        "telegram_id": user.telegram_id,
        "gender": user.gender,
    }


def hhmm(t):
    return t.strftime("%H:%M") if t else None
