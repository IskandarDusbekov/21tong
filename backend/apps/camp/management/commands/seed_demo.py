"""
Lokal ishlab chiqish uchun demo ma'lumot:
  * davom etayotgan oqim (bugun 8-kun) — yigitlar va qizlar rotalari, tarix, mukofotlar;
  * 3 kundan keyin boshlanadigan, qabul ochiq oqim — 3 ta tayyor rota vaqti bilan;
  * startni kutayotgan va tasdiq kutayotgan foydalanuvchilar.
Mini App'dagi "Dev kirish" orqali istalgan demo foydalanuvchi sifatida kirib ko'rish mumkin.

    python manage.py seed_demo          # bir marta yaratadi
    python manage.py seed_demo --reset  # o'chirib, qaytadan yaratadi
"""
import datetime as dt

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.camp import services
from apps.camp.models import Award, Cohort, DayRecord, Immunity, Membership, Notification, Strike, WakeSlot
from apps.community.models import Bounty, BountyCompletion, CoinTransaction, Reflection
from apps.control.models import Stage

COHORT_NAME = "Demo oqim"
NEXT_COHORT_NAME = "Demo: keyingi oqim"
DAYS_PASSED = 7  # bugun 8-kun bo'ladi: budilnik 3-kundan beri surilmoqda

# 9 yigit -> 1-rota (7 kishi) + 2-rota (2 kishi)
BOYS = [
    (1001, "Aziz", "Rahimov", "tashkent_city"), (1002, "Bekzod", "Karimov", "samarkand"),
    (1003, "Jasur", "Tursunov", "fergana"), (1004, "Sardor", "Aliyev", "andijan"),
    (1005, "Doniyor", "Yusupov", "namangan"), (1006, "Otabek", "Saidov", "bukhara"),
    (1007, "Shoxrux", "Ergashev", "tashkent"), (1008, "Ulug'bek", "Nazarov", "kashkadarya"),
    (1009, "Temur", "Qodirov", "khorezm"),
]
GIRLS = [(2001, "Madina", "Usmonova", "tashkent_city"), (2002, "Nilufar", "Hasanova", "samarkand"),
         (2003, "Zarina", "Abdullayeva", "jizzakh")]
WAITING = [(4001, "Sanjar", "Mirzayev", "navoi")]          # qabul qilingan, startni kutmoqda
PENDING = [(3001, "Yangi", "Kelganov", "sirdarya")]       # arizasi ko'rib chiqilmoqda

SLOTS = [(dt.time(6, 0), dt.time(5, 0), "Erta qushlar"), (dt.time(6, 30), dt.time(5, 30), ""),
         (dt.time(7, 0), dt.time(6, 0), "Yengil start")]

REFLECTIONS = {
    1002: "6:30 da turdim, 20 daqiqa yugurdim. Boshida qiyin edi, endi tanam o'rganyapti.",
    1003: "Bugun kechikib qolishimga oz qoldi. Ertaga telefonni uzoqroqqa qo'yaman.",
    2002: "Ertalabki suv va toza havo — kayfiyat butun kun a'lo bo'ldi!",
}
GOAL = "Har kuni erta turib, sport va kitob bilan kunni boshlash."


class Command(BaseCommand):
    help = "Demo oqimlar va foydalanuvchilarni yaratadi (faqat DEBUG)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Avvalgi demo ma'lumotni o'chirish.")

    def register(self, tg, gender, first, last, region, **kw):
        return services.register_user(telegram_id=tg, gender=gender, first_name=first, last_name=last,
                                      region=region, goal=GOAL, **kw)

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("seed_demo faqat DEBUG rejimida ishlaydi.")
        demo_ids = [p[0] for p in BOYS + GIRLS + WAITING + PENDING]
        names = [COHORT_NAME, NEXT_COHORT_NAME]
        if opts["reset"]:
            # Membership.tribe PROTECT — avval a'zoliklar, keyin oqim
            Membership.objects.filter(cohort__name__in=names).delete()
            User.objects.filter(telegram_id__in=demo_ids).delete()
            Cohort.objects.filter(name__in=names).delete()
        elif Cohort.objects.filter(name=COHORT_NAME).exists():
            raise CommandError("Demo allaqachon bor. Qaytadan yaratish uchun: seed_demo --reset")

        today = services.local_now().date()
        cohort = Cohort.objects.create(name=COHORT_NAME, start_date=today - dt.timedelta(days=DAYS_PASSED))

        members = []
        for gender, people in (("M", BOYS), ("F", GIRLS)):
            for tg, first, last, region in people:
                user = self.register(tg, gender, first, last, region,
                                     current_wake_time=dt.time(7, 0), target_wake_time=dt.time(5, 30))
                services.approve_user(user)
                members.append(user.memberships.get(cohort=cohort))

        cohort.status = Cohort.Status.RUNNING
        cohort.save(update_fields=["status"])

        for i, m in enumerate(members):
            for n in range(DAYS_PASSED):
                record = services.ensure_day_record(m, cohort.start_date + dt.timedelta(days=n))
                if i == 2 and n == 3:  # Jasur bir marta kechikkan
                    record.status = DayRecord.Status.FAILED
                    Strike.objects.create(membership=m, day=record, reason=Strike.Reason.LATE)
                elif services.rules.is_rest_day(record.date) and i % 2:
                    record.status = DayRecord.Status.REST
                else:
                    record.status = DayRecord.Status.COMPLETED
                record.save(update_fields=["status"])
            services.ensure_day_record(m, today)
            # O'tgan kunlarga yarasha mukofotlar (bot xabarisiz)
            survived = services.survived_days(m)
            for stage in Stage.objects.filter(day__lte=survived):
                Award.objects.get_or_create(membership=m, stage=stage)

        # Bugungi raport turlicha bo'lsin: kimdir ovozli raport yuborgan, kimdir faqat turgan, kimdir hali yo'q
        for i, m in enumerate(members[1:6], start=1):
            record = services.ensure_day_record(m, today)
            record.woke_at = timezone.now()
            record.phrase = services.rules.random_phrase()
            if i <= 3:
                record.voice_at = timezone.now()
                record.voice_file_id = f"demo-{m.id}"
            record.save(update_fields=["woke_at", "phrase", "voice_at", "voice_file_id"])

        Immunity.objects.create(user=members[0].user, source=Immunity.Source.SUNDAY)

        reading = Bounty.objects.create(cohort=cohort, date=today, title="20 bet kitob o'qish", reward=10)
        Bounty.objects.create(
            cohort=cohort, date=today, title="30 daqiqa sport",
            description="Yugurish, turnik yoki uyda mashq — farqi yo'q.", reward=15,
        )
        for m in members[1:5]:
            c = BountyCompletion.objects.create(bounty=reading, membership=m)
            CoinTransaction.objects.create(user=m.user, amount=reading.reward, reason="bounty", bounty_completion=c)

        by_tg = {m.user.telegram_id: m for m in members}
        for tg, text in REFLECTIONS.items():
            Reflection.objects.create(membership=by_tg[tg], date=today, text=text)

        # Keyingi oqim: 3 kundan keyin start, tayyor rotalar bilan
        nxt = Cohort.objects.create(name=NEXT_COHORT_NAME, start_date=today + dt.timedelta(days=3))
        slots = [WakeSlot.objects.create(cohort=nxt, start_wake_time=s, target_wake_time=t, title=title)
                 for s, t, title in SLOTS]
        for tg, first, last, region in WAITING:
            services.approve_user(self.register(tg, "M", first, last, region, slot_id=slots[0].id))
        for tg, first, last, region in PENDING:
            self.register(tg, "M", first, last, region, slot_id=slots[1].id)

        # Demo foydalanuvchilar soxta — bot ularning xabarlarini (adminlarga "Yangi ariza" ham) yubormasin.
        # Hammasi bitta tranzaksiyada, shuning uchun ishlab turgan bot ularni ko'rib ulgurmaydi.
        Notification.objects.filter(user__telegram_id__in=demo_ids, sent_at__isnull=True).update(sent_at=timezone.now())

        self.stdout.write(self.style.SUCCESS(
            f"Demo tayyor: '{COHORT_NAME}' (bugun {DAYS_PASSED + 1}-kun, {len(members)} kishi) va "
            f"'{NEXT_COHORT_NAME}' (start {nxt.start_date:%d.%m}, {len(SLOTS)} ta rota). "
            f"Startni kutayotgan: {len(WAITING)}, tasdiq kutayotgan: {len(PENDING)}."
        ))
