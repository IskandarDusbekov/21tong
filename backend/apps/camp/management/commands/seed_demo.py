"""
Lokal ishlab chiqish uchun demo ma'lumot: davom etayotgan oqim, yigitlar va qizlar qabilasi,
o'tgan kunlar tarixi, bugungi Bounty va refleksiyalar. Mini App'dagi "Dev kirish" orqali
istalgan demo foydalanuvchi sifatida kirib ko'rish mumkin.

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
from apps.camp.models import Cohort, DayRecord, Joker, Membership, Strike
from apps.community.models import Bounty, BountyCompletion, CoinTransaction, Reflection
from apps.proofs.models import VideoProof

COHORT_NAME = "Demo oqim"
DAYS_PASSED = 7  # bugun 8-kun bo'ladi: budilnik allaqachon surilgan, video talab qilinadi

# 9 yigit -> 1-rota (7 kishi) + 2-rota (2 kishi)
BOYS = [
    (1001, "Aziz"), (1002, "Bekzod"), (1003, "Jasur"), (1004, "Sardor"), (1005, "Doniyor"),
    (1006, "Otabek"), (1007, "Shoxrux"), (1008, "Ulug'bek"), (1009, "Temur"),
]
GIRLS = [(2001, "Madina"), (2002, "Nilufar"), (2003, "Zarina")]
PENDING = [(3001, "Yangi Kelgan")]

REFLECTIONS = {
    1002: "6:50 da turdim, 20 daqiqa yugurdim. Boshida qiyin edi, endi tanam o'rganyapti.",
    1003: "Bugun kechikib qolishimga oz qoldi. Ertaga telefonni uzoqroqqa qo'yaman.",
    2002: "Ertalabki suv va toza havo — kayfiyat butun kun a'lo bo'ldi!",
}


class Command(BaseCommand):
    help = "Demo oqim va foydalanuvchilarni yaratadi (faqat DEBUG)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Avvalgi demo ma'lumotni o'chirish.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("seed_demo faqat DEBUG rejimida ishlaydi.")
        demo_ids = [tg for tg, _ in BOYS + GIRLS + PENDING]
        if opts["reset"]:
            # Membership.tribe PROTECT — avval a'zoliklar, keyin oqim
            Membership.objects.filter(cohort__name=COHORT_NAME).delete()
            Cohort.objects.filter(name=COHORT_NAME).delete()
            User.objects.filter(telegram_id__in=demo_ids).delete()
        elif Cohort.objects.filter(name=COHORT_NAME).exists():
            raise CommandError("Demo allaqachon bor. Qaytadan yaratish uchun: seed_demo --reset")

        today = services.local_now().date()
        cohort = Cohort.objects.create(name=COHORT_NAME, start_date=today - dt.timedelta(days=DAYS_PASSED))

        members = []
        for gender, people in (("M", BOYS), ("F", GIRLS)):
            for tg, name in people:
                user = services.register_user(
                    telegram_id=tg, gender=gender, first_name=name,
                    goal="Har kuni 5:30 da turib, sport va kitob bilan kunni boshlash.",
                )
                services.approve_user(user)
                members.append(services.join_cohort(user, cohort, dt.time(7, 0), dt.time(5, 30)))
        for tg, name in PENDING:
            services.register_user(telegram_id=tg, gender="M", first_name=name, goal="Erta turishni o'rganmoqchiman.")

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

        # Bugungi raport turlicha bo'lsin: kimdir video yuborgan, kimdir faqat turgan, kimdir hali yo'q
        for i, m in enumerate(members[1:6], start=1):
            record = services.ensure_day_record(m, today)
            record.woke_at = timezone.now()
            record.phrase = services.rules.PHRASES[i % len(services.rules.PHRASES)]
            record.save(update_fields=["woke_at", "phrase"])
            if i <= 3:
                VideoProof.objects.create(
                    day=record, telegram_file_id=f"demo-{m.id}", duration=10,
                    status=VideoProof.Status.APPROVED if i < 3 else VideoProof.Status.REVIEWING,
                )

        Joker.objects.create(user=members[0].user, source=Joker.Source.SUNDAY)

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

        self.stdout.write(self.style.SUCCESS(
            f"Demo tayyor: '{COHORT_NAME}', bugun {DAYS_PASSED + 1}-kun. "
            f"{len(BOYS)} yigit, {len(GIRLS)} qiz, {len(PENDING)} tasdiq kutayotgan."
        ))
