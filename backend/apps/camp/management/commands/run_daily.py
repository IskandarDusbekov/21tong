"""
Kunlik jarayon. Har kuni yarim tundan keyin (masalan 00:05) cron/scheduler orqali ishga tushiriladi:

  1. Boshlanish sanasi kelgan oqimlarni RUNNING, tugaganlarini FINISHED qiladi.
  2. Kechagi barcha PENDING kunlarni baholaydi (Strike / Joker / bosqich).
  3. Bugungi kun yozuvlarini (budilnik vaqti bilan) yaratadi.
"""
import datetime as dt

from django.core.management.base import BaseCommand

from apps.camp import services
from apps.camp.models import Cohort, DayRecord, Membership


class Command(BaseCommand):
    help = "Kunni yopadi va yangisini ochadi."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Bugungi sana (YYYY-MM-DD), test uchun.")

    def handle(self, *args, **opts):
        today = dt.date.fromisoformat(opts["date"]) if opts["date"] else services.local_now().date()
        yesterday = today - dt.timedelta(days=1)

        started = Cohort.objects.filter(status=Cohort.Status.RECRUITING, start_date__lte=today).update(
            status=Cohort.Status.RUNNING
        )

        evaluated = 0
        for record in DayRecord.objects.filter(date__lte=yesterday, status=DayRecord.Status.PENDING):
            services.evaluate_day(record)
            evaluated += 1

        # Kecha umuman yozuvi ochilmagan (botga kirmagan) faollar ham baholanadi
        for m in Membership.objects.filter(status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RUNNING):
            if m.cohort.day_number(yesterday) and not m.days.filter(date=yesterday).exists():
                services.evaluate_day(services.ensure_day_record(m, yesterday))
                evaluated += 1

        finished = 0
        for cohort in Cohort.objects.filter(status=Cohort.Status.RUNNING, start_date__lte=today):
            if cohort.end_date < today:
                cohort.status = Cohort.Status.FINISHED
                cohort.save(update_fields=["status"])
                cohort.memberships.filter(status=Membership.Status.ACTIVE).update(status=Membership.Status.FINISHED)
                finished += 1

        opened = 0
        for m in Membership.objects.filter(
            status=Membership.Status.ACTIVE, cohort__status=Cohort.Status.RUNNING
        ).select_related("cohort", "tribe"):
            if m.cohort.day_number(today):
                services.ensure_day_record(m, today)
                opened += 1

        self.stdout.write(self.style.SUCCESS(
            f"{today}: {started} oqim boshlandi, {evaluated} kun baholandi, "
            f"{finished} oqim yakunlandi, {opened} kun ochildi."
        ))
