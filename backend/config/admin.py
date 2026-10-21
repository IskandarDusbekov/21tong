"""
21tong admin sayti: bosh sahifada bugungi holat (statistika) va tezkor havolalar.
"""
from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.db.models import Count, Q
from django.urls import reverse


class TongAdminSite(admin.AdminSite):
    site_header = "21 Tong — qo'mondonlik"
    site_title = "21 Tong admin"
    index_title = "Boshqaruv paneli"

    def index(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "dashboard": dashboard()}
        return super().index(request, extra_context)


def dashboard():
    from apps.accounts.models import User
    from apps.camp import services
    from apps.camp.models import Cohort, DayRecord, Membership, Strike
    from apps.proofs.models import VideoProof

    today = services.local_now().date()
    running = list(Cohort.objects.filter(status=Cohort.Status.RUNNING).order_by("start_date"))
    active = Membership.objects.filter(status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RUNNING)
    records = DayRecord.objects.filter(date=today, membership__in=active)
    total_today = active.count()
    done = records.filter(Q(voice_at__isnull=False) | Q(video__status__in=["approved", "reviewing"]) | Q(status="completed")).count()
    woke = records.filter(woke_at__isnull=False).count()

    def url(name, query=""):
        return reverse(f"admin:{name}") + (f"?{query}" if query else "")

    return {
        "today": today,
        "cohorts": [
            {"name": c.name, "day": c.day_number(today), "duration": c.duration_days,
             "members": c.memberships.filter(status=Membership.Status.ACTIVE).count()}
            for c in running
        ],
        "recruiting": Cohort.objects.filter(status=Cohort.Status.RECRUITING).annotate(n=Count("memberships")),
        "cards": [
            {"label": "Yangi arizalar", "value": User.objects.filter(status=User.Status.PENDING).count(),
             "url": url("accounts_user_changelist", "status__exact=pending"), "tone": "warn"},
            {"label": "Faol ishtirokchilar", "value": total_today,
             "url": url("camp_membership_changelist", "status__exact=active"), "tone": ""},
            {"label": "Bugun raport berdi", "value": f"{done}/{total_today}",
             "url": url("camp_dayrecord_changelist", f"date={today.isoformat()}"), "tone": "ok"},
            {"label": "Turdi, raport yo'q", "value": max(woke - done, 0),
             "url": url("camp_dayrecord_changelist", f"date={today.isoformat()}"), "tone": "warn"},
            {"label": "Tekshiruvdagi videolar", "value": VideoProof.objects.filter(status="reviewing").count(),
             "url": url("proofs_videoproof_changelist", "status__exact=reviewing"), "tone": ""},
            {"label": "Bugungi ogohlantirishlar",
             "value": Strike.objects.filter(created_at__date=today, revoked=False, cancelled_by_immunity=False).count(),
             "url": url("camp_strike_changelist"), "tone": "bad"},
        ],
        "links": [
            ("Lager sozlamalari", reverse("admin:control_campsettings_change", args=[1])),
            ("Bot xabarlari", url("control_botmessage_changelist")),
            ("O'qiladigan gaplar", url("control_phrase_changelist")),
            ("Bosqichlar", url("control_stage_changelist")),
            ("Ommaviy xabar yuborish", url("control_broadcast_add")),
            ("Yangi oqim ochish", url("camp_cohort_add")),
        ],
    }


class TongAdminConfig(AdminConfig):
    default_site = "config.admin.TongAdminSite"
