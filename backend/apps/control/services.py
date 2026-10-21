from apps.accounts.models import User
from apps.camp.models import Cohort, Membership, Notification

from .models import Broadcast


def broadcast_recipients(b: Broadcast):
    A = Broadcast.Audience
    if b.audience == A.PENDING:
        users = User.objects.filter(status=User.Status.PENDING)
    elif b.audience == A.APPROVED:
        users = User.objects.filter(status=User.Status.APPROVED)
    else:
        members = Membership.objects.filter(status=Membership.Status.ACTIVE)
        if b.audience == A.ACTIVE:
            members = members.filter(cohort__status=Cohort.Status.RUNNING)
        elif b.audience == A.COHORT:
            members = members.filter(cohort=b.cohort)
        elif b.audience == A.SQUAD:
            members = members.filter(squad=b.squad)
        users = User.objects.filter(pk__in=members.values("user"))
    if b.gender:
        users = users.filter(gender=b.gender)
    return users.filter(telegram_id__isnull=False)


def send_broadcast(b: Broadcast):
    users = list(broadcast_recipients(b))
    Notification.objects.bulk_create([
        Notification(user=u, kind=Notification.Kind.BROADCAST, payload={"text": b.text, "broadcast_id": b.id})
        for u in users
    ])
    b.sent_count = len(users)
    b.save(update_fields=["sent_count"])
    return len(users)
