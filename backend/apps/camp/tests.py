import datetime as dt
import hashlib
import hmac
import json
import tempfile
import time
from unittest import mock
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.auth import validate_init_data
from apps.accounts.models import User
from apps.camp import rules, services
from django.core.cache import cache

from apps.camp.models import Cohort, DayRecord, Immunity, Membership, Notification, Strike, WakeSlot
from apps.control.models import BotMessage, CampSettings
from apps.community import services as community
from apps.proofs import services as proofs
from apps.proofs.models import VideoProof

TZ = ZoneInfo("Asia/Tashkent")
MONDAY = dt.date(2026, 11, 2)
DAY8 = MONDAY + dt.timedelta(days=7)  # dushanba, 8-kun: budilnik 6 marta surilgan (06:30)


def at(date, h, m=0):
    return dt.datetime.combine(date, dt.time(h, m), tzinfo=TZ)


class RulesTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_kaizen_shift_from_day3(self):
        start, target = dt.time(7, 0), dt.time(5, 30)
        self.assertEqual(rules.alarm_time_for_day(start, target, 1), dt.time(7, 0))
        self.assertEqual(rules.alarm_time_for_day(start, target, 2), dt.time(7, 0))
        self.assertEqual(rules.alarm_time_for_day(start, target, 3), dt.time(6, 55))
        self.assertEqual(rules.alarm_time_for_day(start, target, 8), dt.time(6, 30))
        self.assertEqual(rules.alarm_time_for_day(start, target, 21), dt.time(5, 30))

    def test_kaizen_follows_admin_settings(self):
        set_rules(shift_from_day=7, shift_step_minutes=10)
        start, target = dt.time(7, 0), dt.time(5, 30)
        self.assertEqual(rules.alarm_time_for_day(start, target, 6), dt.time(7, 0))
        self.assertEqual(rules.alarm_time_for_day(start, target, 8), dt.time(6, 40))

    def test_threshold(self):
        self.assertEqual(rules.approval_threshold(3), 2)
        self.assertEqual(rules.approval_threshold(2), 2)
        self.assertEqual(rules.approval_threshold(1), 1)

    def test_stage(self):
        self.assertIsNone(rules.stage_for(2))
        self.assertEqual(rules.stage_for(3)["name"], "Omon qolgan")
        self.assertEqual(rules.stage_for(21)["name"], "Temir Iroda")


def set_rules(**values):
    c = CampSettings.load()
    for k, v in values.items():
        setattr(c, k, v)
    c.save()


class CampTestCase(TestCase):
    def setUp(self):
        cache.clear()  # sozlamalar keshi testlar orasida qolib ketmasin
        self.cohort = Cohort.objects.create(name="1-oqim", start_date=MONDAY)

    def make_member(self, tg, gender="M", start=dt.time(7, 0), target=dt.time(5, 30)):
        user = services.register_user(telegram_id=tg, gender=gender, goal="5:30 da turish", first_name=f"U{tg}")
        services.approve_user(user)
        self.cohort.status = Cohort.Status.RECRUITING
        self.cohort.save()
        m = services.join_cohort(user, self.cohort, start, target)
        self.cohort.status = Cohort.Status.RUNNING
        self.cohort.save()
        return m

    def complete_morning(self, m, date, proof=True):
        """Uyg'ondim + kunga mos raport (ovoz; sozlamada yoqilgan bo'lsa — video)."""
        record = services.ensure_day_record(m, date)
        woke = at(date, record.alarm_time.hour, record.alarm_time.minute)
        services.press_wake(m, woke)
        if not proof:
            return None
        if rules.video_required(record.day_number):
            return proofs.submit_video(m, f"file-{m.id}-{date}", 10, woke + dt.timedelta(minutes=3))
        return services.record_voice(m, f"voice-{m.id}", woke + dt.timedelta(minutes=1))


class OnboardingTests(CampTestCase):
    def test_gender_cannot_change(self):
        services.register_user(telegram_id=1, gender="F", goal="x")
        with self.assertRaises(services.RuleError):
            services.register_user(telegram_id=1, gender="M", goal="x")

    def test_referral_gives_no_immunity_by_default(self):
        a = services.register_user(telegram_id=1, gender="M", goal="x")
        b = services.register_user(telegram_id=2, gender="M", goal="x", referral_code=a.referral_code)
        services.approve_user(b)
        self.assertEqual(services.immunities_available(a), 0)

    def test_referral_immunity_once_when_enabled(self):
        set_rules(referral_immunity=True)
        a = services.register_user(telegram_id=1, gender="M", goal="x")
        b = services.register_user(telegram_id=2, gender="M", goal="x", referral_code=a.referral_code)
        c = services.register_user(telegram_id=3, gender="F", goal="x", referral_code=a.referral_code)
        services.approve_user(b)
        services.approve_user(c)
        self.assertEqual(services.immunities_available(a), 1)

    def test_tribes_split_by_gender(self):
        boy = self.make_member(1, "M")
        girl = self.make_member(2, "F")
        self.assertNotEqual(boy.tribe_id, girl.tribe_id)
        self.assertEqual(boy.tribe.start_wake_time, girl.tribe.start_wake_time)


class ReviewTests(CampTestCase):
    def setUp(self):
        super().setUp()
        set_rules(video_from_day=7)

    def test_reviewers_are_same_gender_only(self):
        boys = [self.make_member(i, "M") for i in range(1, 6)]
        for i in range(10, 15):
            self.make_member(i, "F")
        day = MONDAY + dt.timedelta(days=6)  # video talab qilinadigan kun
        proof = self.complete_morning(boys[0], day)
        reviewers = list(proof.reviews.select_related("reviewer__tribe"))
        self.assertEqual(len(reviewers), 3)
        for r in reviewers:
            self.assertEqual(r.reviewer.tribe.gender, "M")
            self.assertNotEqual(r.reviewer_id, boys[0].id)

    def test_two_of_three_approve(self):
        members = [self.make_member(i) for i in range(1, 5)]
        proof = self.complete_morning(members[0], DAY8)
        reviews = list(proof.reviews.select_related("reviewer"))
        proofs.cast_vote(reviews[0], reviews[0].reviewer, True)
        proof.refresh_from_db()
        self.assertEqual(proof.status, VideoProof.Status.REVIEWING)
        proofs.cast_vote(reviews[1], reviews[1].reviewer, True)
        proof.refresh_from_db()
        self.assertEqual(proof.status, VideoProof.Status.APPROVED)

    def test_cannot_vote_on_others_review(self):
        members = [self.make_member(i) for i in range(1, 5)]
        proof = self.complete_morning(members[0], DAY8)
        review = proof.reviews.first()
        with self.assertRaises(services.RuleError):
            proofs.cast_vote(review, members[0], True)

    def test_chat_shows_video_with_review_controls(self):
        """Rotadagi video chatda ko'rinadi; tekshiruvchiga tasdiq tugmasi (can_review)."""
        members = [self.make_member(i) for i in range(1, 5)]
        proof = self.complete_morning(members[0], DAY8)
        reviewer = proof.reviews.first().reviewer
        now = at(DAY8, 7, 0)
        # Egasining o'zi — tasdiqlay olmaydi
        own = next(it for it in community.squad_chat(members[0], now)["items"]
                   if it["kind"] == "video" and it["me"])
        self.assertFalse(own["can_review"])
        self.assertEqual(own["proof_id"], proof.id)
        # Tekshiruvchi — tasdiqlay oladi
        vid = next(it for it in community.squad_chat(reviewer, now)["items"]
                   if it["kind"] == "video" and not it["me"])
        self.assertTrue(vid["can_review"])
        # Boshqa rotadosh (tekshiruvchi emas) — tugma yo'q
        other = next((m for m in members if m.id not in (members[0].id, reviewer.id)
                      and not proof.reviews.filter(reviewer=m).exists()), None)
        if other:
            row = next(it for it in community.squad_chat(other, now)["items"] if it["kind"] == "video")
            self.assertFalse(row["can_review"])


class EvaluationTests(CampTestCase):
    def evaluate(self, m, date):
        return services.evaluate_day(services.ensure_day_record(m, date))

    def test_completed_day(self):
        m = self.make_member(1)
        self.complete_morning(m, MONDAY)
        self.assertEqual(self.evaluate(m, MONDAY).status, DayRecord.Status.COMPLETED)

    def test_late_wake_gives_strike(self):
        m = self.make_member(1)
        services.press_wake(m, at(MONDAY, 7, 6))
        record = self.evaluate(m, MONDAY)
        self.assertEqual(record.status, DayRecord.Status.FAILED)
        self.assertEqual(m.strikes.get().reason, Strike.Reason.LATE)

    def test_missing_voice_before_day7(self):
        m = self.make_member(1)
        self.complete_morning(m, MONDAY, proof=False)
        self.evaluate(m, MONDAY)
        self.assertEqual(m.strikes.get().reason, Strike.Reason.NO_VOICE)

    def test_missing_video_after_day7(self):
        set_rules(video_from_day=7)
        m = self.make_member(1)
        self.complete_morning(m, DAY8, proof=False)
        self.evaluate(m, DAY8)
        self.assertEqual(m.strikes.get().reason, Strike.Reason.NO_VIDEO)

    def test_three_strikes_out(self):
        m = self.make_member(1)
        for i in range(3):
            self.evaluate(m, MONDAY + dt.timedelta(days=i))
        m.refresh_from_db()
        self.assertEqual(m.status, Membership.Status.EXPELLED)
        self.assertTrue(Notification.objects.filter(user=m.user, kind="expelled").exists())

    def test_immunity_cancels_strike(self):
        m = self.make_member(1)
        Immunity.objects.create(user=m.user, source=Immunity.Source.ADMIN)
        for i in range(3):
            self.evaluate(m, MONDAY + dt.timedelta(days=i))
        m.refresh_from_db()
        self.assertEqual(m.status, Membership.Status.ACTIVE)
        self.assertEqual(m.active_strikes, 2)

    def test_sunday_rest_and_immunity(self):
        sleeper, early = self.make_member(1), self.make_member(2)
        sunday = MONDAY + dt.timedelta(days=6)
        self.complete_morning(early, sunday)
        self.assertEqual(self.evaluate(sleeper, sunday).status, DayRecord.Status.REST)
        self.assertEqual(self.evaluate(early, sunday).status, DayRecord.Status.COMPLETED)
        self.assertEqual(sleeper.strikes.count(), 0)
        self.assertEqual(services.immunities_available(early.user), 1)

    def test_freeze_only_evening_once(self):
        m = self.make_member(1)
        with self.assertRaises(services.RuleError):
            services.request_freeze(m, now=at(MONDAY, 12))
        services.request_freeze(m, now=at(MONDAY, 21))
        m.refresh_from_db()
        tuesday = MONDAY + dt.timedelta(days=1)
        self.assertEqual(self.evaluate(m, tuesday).status, DayRecord.Status.FROZEN)
        with self.assertRaises(services.RuleError):
            services.request_freeze(m, now=at(tuesday, 21))


class CampDisciplineTests(CampTestCase):
    def test_squads_of_seven(self):
        members = [self.make_member(i) for i in range(1, 9)]
        self.assertEqual({m.squad.number for m in members[:7]}, {1})
        self.assertEqual(members[7].squad.number, 2)
        self.assertEqual(members[7].squad.tribe_id, members[0].tribe_id)
        girl = self.make_member(100, "F")
        # Boshqa qabila — lekin nomi takrorlanmaydi: raqam oqim bo'yicha davom etadi
        self.assertEqual(girl.squad.number, 3)
        self.assertNotEqual(girl.squad_id, members[0].squad_id)

    def test_reviewers_prefer_own_squad(self):
        set_rules(video_from_day=7)
        members = [self.make_member(i) for i in range(1, 15)]  # 2 ta to'liq rota
        proof = self.complete_morning(members[0], DAY8)
        squads = {r.reviewer.squad_id for r in proof.reviews.select_related("reviewer")}
        self.assertEqual(squads, {members[0].squad_id})

    def test_wake_gives_phrase_and_proof_kind(self):
        m = self.make_member(1)
        record = services.press_wake(m, at(MONDAY, 7, 0))
        self.assertTrue(record.phrase)
        progress = services.day_progress(record)
        self.assertEqual(progress["proof_kind"], "voice")
        self.assertEqual(progress["proof_deadline"], "07:05")  # ovozli raport — 5 daqiqa

    def test_proof_requires_wake_and_both_tasks_daily(self):
        """Endi har kuni 3 topshiriq: ovoz ham, yurish videosi ham — bir-birini istisno qilmaydi."""
        set_rules(video_from_day=7)
        m = self.make_member(1)
        with self.assertRaises(services.RuleError):
            services.record_voice(m, "v", at(MONDAY, 7, 1))  # "Uyg'ondim" bosilmagan
        services.press_wake(m, at(MONDAY, 7, 0))
        proofs.submit_video(m, "f", 10, at(MONDAY, 7, 2))  # 1-kun — video ixtiyoriy, lekin qabul
        services.press_wake(m, at(DAY8, 6, 30))
        rec = services.record_voice(m, "v", at(DAY8, 6, 32))  # 8-kun — video majburiy, ovoz ham qabul
        self.assertFalse(rec.voice_late)

    def test_required_video_keeps_strict_deadline(self):
        set_rules(video_from_day=1, video_deadline_minutes=20)
        m = self.make_member(1)
        services.press_wake(m, at(MONDAY, 7, 0))
        with self.assertRaises(services.RuleError):
            proofs.submit_video(m, "f", 10, at(MONDAY, 7, 30))  # majburiy kunda 20 daqiqadan kech

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_task_coins_awarded_once(self):
        set_rules(coins_wake=5, coins_voice=5, coins_water=7, coins_video=10)
        m = self.make_member(1)
        rec = services.press_wake(m, at(MONDAY, 7, 1))  # vaqtida — tanga
        services.press_wake(m, at(MONDAY, 7, 2))  # qayta bosish — yangi tanga yo'q
        services.record_voice(m, "v", at(MONDAY, 7, 4))  # muddatida — tanga
        upload = SimpleUploadedFile("w.jpg", b"img", content_type="image/jpeg")
        services.record_water(m, upload, at(MONDAY, 7, 10))
        with self.assertRaises(services.RuleError):
            services.record_water(m, SimpleUploadedFile("w2.jpg", b"img"), at(MONDAY, 7, 11))
        proof = proofs.submit_video(m, "f", 10, at(MONDAY, 7, 12))  # tekshiruvchi yo'q — avtomatik tasdiq
        self.assertEqual(proof.status, VideoProof.Status.APPROVED)
        self.assertEqual(community.coin_balance(m.user), 5 + 5 + 7 + 10)
        coins = services.day_progress(rec)["coins"]
        self.assertTrue(all(t["earned"] for t in coins.values()))

    def test_late_tasks_give_no_coins(self):
        set_rules(coins_wake=5, coins_voice=5)
        m = self.make_member(1)
        services.press_wake(m, at(MONDAY, 7, 30))  # 5 daqiqalik muddatdan kech
        rec = services.record_voice(m, "v", at(MONDAY, 7, 40))  # kech ovoz — qabul, lekin tangasiz
        self.assertTrue(rec.voice_late)
        self.assertEqual(community.coin_balance(m.user), 0)

    def test_on_time_voice_counts(self):
        m = self.make_member(1)
        services.press_wake(m, at(MONDAY, 7, 0))
        rec = services.record_voice(m, "v", at(MONDAY, 7, 4))
        self.assertFalse(rec.voice_late)
        services.evaluate_day(rec)
        rec.refresh_from_db()
        self.assertEqual(rec.status, "completed")

    def test_late_voice_accepted_but_not_counted(self):
        """Kech raport chatga tushadi (qabul qilinadi), lekin kun bajarilgan hisoblanmaydi."""
        m = self.make_member(1)
        services.press_wake(m, at(MONDAY, 7, 0))
        rec = services.record_voice(m, "v", at(MONDAY, 7, 6))
        self.assertTrue(rec.voice_late)
        self.assertFalse(services.day_progress(rec)["proof_done"])
        services.evaluate_day(rec)
        rec.refresh_from_db()
        self.assertEqual(rec.status, "failed")

    def test_application_notifies_admins_and_approval_joins_squad(self):
        user = services.register_user(
            telegram_id=55, gender="F", goal="Erta turish", first_name="Dilnoza",
            current_wake_time=dt.time(7, 0), target_wake_time=dt.time(5, 30),
        )
        app = Notification.objects.get(user=user, kind="new_application")
        self.assertEqual(app.payload["current_wake_time"], "07:00")
        services.approve_user(user)
        m = Membership.objects.get(user=user)
        self.assertEqual(m.squad.number, 1)
        self.assertEqual(m.target_wake_time, dt.time(5, 30))
        approved = Notification.objects.get(user=user, kind="approved")
        self.assertEqual(approved.payload["squad"], "1-rota")

    def test_squad_report(self):
        a, b, c = self.make_member(1), self.make_member(2), self.make_member(3)
        self.complete_morning(a, MONDAY)
        self.complete_morning(b, MONDAY, proof=False)
        report = services.squad_report(a.squad, MONDAY)
        statuses = {r["telegram_id"]: r["status"] for r in report["members"]}
        self.assertEqual(statuses, {1: "done", 2: "woke", 3: "absent"})
        self.assertEqual((report["done"], report["total"]), (1, 3))

    def test_strike_shows_in_squad_chat(self):
        m = self.make_member(1)
        services.evaluate_day(services.ensure_day_record(m, MONDAY))
        self.assertTrue(Notification.objects.filter(user=m.user, kind="strike").exists())
        chat = community.squad_chat(m)
        self.assertTrue(any(it["type"] == "strike" for it in chat["items"]))


class ChatTests(CampTestCase):
    def test_chat_post_only_in_window(self):
        m = self.make_member(1)
        with self.assertRaises(services.RuleError):
            community.post_chat_message(m, "salom", at(MONDAY, 15))  # oyna yopiq
        msg = community.post_chat_message(m, "salom", at(MONDAY, 21))  # kechki oyna ochiq
        self.assertEqual(msg.text, "salom")
        chat = community.squad_chat(m)  # created_at bugungi — jonli lentada ko'rinadi
        self.assertTrue(any(it["type"] == "message" and it["text"] == "salom" for it in chat["items"]))

    def test_chat_report_card_only_after_proof(self):
        """Faqat uyg'ongan (raport yubormagan) odam chatda karta sifatida ko'rinmaydi — safda sanaladi."""
        m = self.make_member(1)
        services.press_wake(m, at(MONDAY, 7, 0))
        chat = community.squad_chat(m, at(MONDAY, 8))
        self.assertFalse(any(it["type"] == "report" for it in chat["items"]))
        services.record_voice(m, "v", at(MONDAY, 7, 2))
        chat = community.squad_chat(m, at(MONDAY, 8))
        self.assertTrue(any(it["type"] == "report" for it in chat["items"]))

    def test_admin_review_marks_report(self):
        m = self.make_member(1)
        rec = self.complete_morning(m, MONDAY)
        self.assertTrue(services.admin_review_report(rec))
        self.assertFalse(services.admin_review_report(rec))  # idempotent
        rec.refresh_from_db()
        self.assertTrue(services.day_progress(rec)["admin_reviewed"])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PhotoTests(CampTestCase):
    def _img(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, "JPEG")
        return SimpleUploadedFile("a.jpg", buf.getvalue(), "image/jpeg")

    def test_upload_limit_and_vote(self):
        from apps.community.models import PhotoEntry

        a, b = self.make_member(1), self.make_member(2)
        community.upload_photo(a, self._img())
        community.upload_photo(a, self._img())
        with self.assertRaises(services.RuleError):
            community.upload_photo(a, self._img())  # 2 tadan oshmaydi

        feed = community.photo_feed(b)
        self.assertEqual(len(feed["entries"]), 2)
        entry = PhotoEntry.objects.filter(membership=a).first()
        self.assertTrue(community.vote_photo(b, entry))   # ovoz berildi
        self.assertFalse(community.vote_photo(b, entry))  # qayta bosilsa — olinadi
        with self.assertRaises(services.RuleError):
            community.vote_photo(a, entry)  # o'ziga ovoz bermaydi

    def test_photo_isolated_by_gender(self):
        boy, girl = self.make_member(1, "M"), self.make_member(2, "F")
        community.upload_photo(boy, self._img())
        self.assertEqual(len(community.photo_feed(girl)["entries"]), 0)

    def test_ranking_has_three_levels_and_votes_count(self):
        a, b = self.make_member(1), self.make_member(2)
        community.upload_photo(a, self._img())
        entry = a.photo_entries.first()
        community.vote_photo(b, entry)
        r = community.ranking(a)
        self.assertEqual(set(r), {"my_squad_name", "squad", "squads", "tribe_top"})
        me = next(x for x in r["squad"] if x["me"])
        self.assertEqual(me["votes"], 1)
        self.assertGreaterEqual(me["points"], 5)  # 1 ovoz = 5 ball


class CommunityTests(CampTestCase):
    def test_reflection_only_in_evening_window(self):
        m = self.make_member(1)
        with self.assertRaises(services.RuleError):
            community.add_reflection(m, "Yaxshi", at(MONDAY, 15))
        community.add_reflection(m, "Yaxshi", at(MONDAY, 21))
        with self.assertRaises(services.RuleError):
            community.add_reflection(m, "x" * 201, at(MONDAY + dt.timedelta(days=1), 21))

    def test_feed_and_fire_gender_isolated(self):
        boy1, boy2, girl = self.make_member(1, "M"), self.make_member(2, "M"), self.make_member(3, "F")
        r = community.add_reflection(boy1, "Zo'r kun", at(MONDAY, 21))
        community.give_fire(boy2, r)
        with self.assertRaises(services.RuleError):
            community.give_fire(girl, r)
        self.assertEqual(list(community.feed(girl, MONDAY)), [])
        self.assertEqual(community.feed(boy2, MONDAY).get().fire_count, 1)


def signed_init_data(user, token, auth_date=None):
    data = {"auth_date": str(auth_date or int(time.time())), "user": json.dumps(user)}
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@override_settings(TELEGRAM_BOT_TOKEN="123:abc", BOT_API_SECRET="s3cret")
class ApiTests(CampTestCase):
    def test_init_data_validation(self):
        good = signed_init_data({"id": 42}, "123:abc")
        self.assertEqual(validate_init_data(good, "123:abc", 3600)["id"], 42)
        with self.assertRaises(ValueError):
            validate_init_data(good, "999:zzz", 3600)
        with self.assertRaises(ValueError):
            validate_init_data(signed_init_data({"id": 42}, "123:abc", 1), "123:abc", 3600)

    def test_bot_requires_secret(self):
        client = APIClient()
        payload = {"telegram_id": 7, "gender": "F", "goal": "Erta turish"}
        self.assertEqual(client.post("/api/bot/users/register/", payload, format="json").status_code, 403)
        resp = client.post("/api/bot/users/register/", payload, format="json", HTTP_X_BOT_SECRET="s3cret")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], "pending")
        png = client.get("/api/bot/users/7/manifest.png", HTTP_X_BOT_SECRET="s3cret")
        self.assertEqual(png["Content-Type"], "image/png")

    def test_journey_calendar_and_stages(self):
        m = self.make_member(1)
        for i in range(3):
            day = MONDAY + dt.timedelta(days=i)
            self.complete_morning(m, day)
            services.evaluate_day(services.ensure_day_record(m, day))
        j = services.journey(m, at(MONDAY + dt.timedelta(days=3), 21))
        self.assertEqual(j["survived"], 3)
        self.assertEqual(j["stage"]["name"], "Omon qolgan")
        self.assertEqual(j["next_stage"]["name"], "Moslashgan")
        self.assertEqual(len(j["days"]), 21)
        self.assertEqual(j["days"][0]["status"], "completed")
        self.assertTrue(j["days"][3]["today"])
        self.assertEqual(j["days"][20]["status"], "future")
        self.assertEqual(j["days"][7]["alarm_time"], "06:30")
        self.assertTrue(j["windows"]["evening"]["open"])
        self.assertFalse(j["windows"]["morning"]["open"])

    def test_dev_login_only_when_enabled(self):
        self.make_member(42)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="dev 42")
        with override_settings(DEV_LOGIN=True):
            self.assertEqual(client.get("/api/app/me/").status_code, 200)
        with override_settings(DEV_LOGIN=False):
            self.assertIn(client.get("/api/app/me/").status_code, (401, 403))
            self.assertEqual(client.get("/api/app/dev/users/").status_code, 404)

    def test_bot_admin_approve_and_wake(self):
        client = APIClient()
        client.credentials(HTTP_X_BOT_SECRET="s3cret")
        client.post("/api/bot/users/register/", {
            "telegram_id": 9, "gender": "M", "goal": "Erta turish", "first_name": "Ali",
            "current_wake_time": "07:00", "target_wake_time": "05:30",
        }, format="json")
        self.assertEqual(len(client.get("/api/bot/users/pending/").json()), 1)
        resp = client.post("/api/bot/users/9/approve/")
        self.assertEqual(resp.json()["membership"]["squad"], "1-rota")
        self.assertEqual(client.post("/api/bot/users/9/approve/").status_code, 400)

    def test_miniapp_wake(self):
        m = self.make_member(42)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="tma " + signed_init_data({"id": 42}, "123:abc"))
        with mock.patch("apps.camp.services.timezone.now", return_value=at(MONDAY, 6, 59)):
            me = client.get("/api/app/me/").json()
            self.assertEqual(me["today"]["alarm_time"], "07:00")
            resp = client.post("/api/app/wake/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["woke"])


class AdminControlTests(CampTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser("boss", password="test-pass-123")
        self.client.force_login(self.admin)

    def test_every_admin_page_opens(self):
        from django.contrib import admin as django_admin
        from django.urls import reverse

        m = self.make_member(1)
        self.complete_morning(m, MONDAY)
        services.evaluate_day(services.ensure_day_record(m, MONDAY + dt.timedelta(days=1)))  # ogohlantirish
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        for model, model_admin in django_admin.site._registry.items():
            info = (model._meta.app_label, model._meta.model_name)
            resp = self.client.get(reverse("admin:%s_%s_changelist" % info), follow=True)
            self.assertEqual(resp.status_code, 200, f"{info} ro'yxati ochilmadi")
            obj = model.objects.first()
            if obj is not None:
                resp = self.client.get(reverse("admin:%s_%s_change" % info, args=[obj.pk]))
                self.assertEqual(resp.status_code, 200, f"{info} sahifasi ochilmadi")

    def test_max_strikes_from_settings(self):
        set_rules(max_strikes=2)
        m = self.make_member(1)
        for i in range(2):
            services.evaluate_day(services.ensure_day_record(m, MONDAY + dt.timedelta(days=i)))
        m.refresh_from_db()
        self.assertEqual(m.status, Membership.Status.EXPELLED)

    def test_admin_actions_strike_revoke_restore(self):
        from django.urls import reverse

        m = self.make_member(1)
        url = reverse("admin:camp_membership_changelist")
        for action in ("give_strike", "give_strike", "give_strike"):
            self.client.post(url, {"action": action, "_selected_action": [m.pk]})
        m.refresh_from_db()
        self.assertEqual(m.status, Membership.Status.EXPELLED)
        self.client.post(url, {"action": "revoke_last_strike", "_selected_action": [m.pk]})
        self.client.post(url, {"action": "restore", "_selected_action": [m.pk]})
        m.refresh_from_db()
        self.assertEqual((m.status, m.active_strikes), (Membership.Status.ACTIVE, 2))
        self.client.post(url, {"action": "give_immunity", "_selected_action": [m.pk]})
        self.assertEqual(services.immunities_available(m.user), 1)

    def test_bot_message_validation(self):
        msg = BotMessage.objects.get(key="voice_ok")
        msg.text = "✅ {day}-kun, {max_strikes} ta"
        msg.full_clean()
        msg.text = "{nomalum}"
        with self.assertRaises(ValidationError):
            msg.full_clean()
        msg.text = "buzilgan {day"
        with self.assertRaises(ValidationError):
            msg.full_clean()

    def test_settings_page_saves(self):
        from django.urls import reverse

        url = reverse("admin:control_campsettings_change", args=[1])
        form = self.client.get(url).context["adminform"].form
        data = {k: v for k, v in form.initial.items() if v is not None}
        data = {k: (v.strftime("%H:%M") if isinstance(v, dt.time) else v) for k, v in data.items()}
        data.update({k: "on" for k, v in data.items() if v is True})
        for k in [k for k, v in data.items() if v is False]:
            data.pop(k)
        data["voice_deadline_minutes"] = 10
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302, resp.content[:500])
        cache.clear()
        self.assertEqual(rules.current().voice_deadline_minutes, 10)

    def test_broadcast_to_girls_only(self):
        from apps.control.models import Broadcast
        from apps.control.services import send_broadcast

        self.make_member(1, "M")
        girl = self.make_member(2, "F")
        b = Broadcast.objects.create(text="Diqqat!", audience=Broadcast.Audience.ACTIVE, gender="F")
        self.assertEqual(send_broadcast(b), 1)
        self.assertEqual(Notification.objects.get(kind="broadcast").user, girl.user)

    def test_registration_closed(self):
        set_rules(registration_open=False)
        with self.assertRaises(services.RuleError):
            services.register_user(telegram_id=777, gender="M", goal="Erta turish")


@override_settings(BOT_API_SECRET="s3cret")
class BotConfigApiTests(CampTestCase):
    def test_config_has_messages_and_settings(self):
        set_rules(voice_deadline_minutes=7)
        data = APIClient().get("/api/bot/config/", HTTP_X_BOT_SECRET="s3cret").json()
        self.assertEqual(data["settings"]["voice_deadline"], 7)
        self.assertIn("{phrase}", data["messages"]["order_voice"])


PNG = bytes([0x89]) + b"PNG"


class SlotsAwardsCountdownTests(CampTestCase):
    def setUp(self):
        super().setUp()
        self.cohort.status = Cohort.Status.RECRUITING
        self.cohort.save()
        self.slot = WakeSlot.objects.create(cohort=self.cohort, start_wake_time=dt.time(6), target_wake_time=dt.time(5))

    def apply(self, tg, gender="M", **kw):
        return services.register_user(
            telegram_id=tg, gender=gender, goal="Erta turish", first_name="Ali", last_name="Valiyev",
            region="samarkand", slot_id=self.slot.id, **kw,
        )

    def test_application_with_slot_places_into_slot_time(self):
        u = self.apply(10)
        self.assertEqual((u.last_name, u.region, u.preferred_slot_id), ("Valiyev", "samarkand", self.slot.id))
        services.approve_user(u)
        m = Membership.objects.get(user=u)
        self.assertEqual((m.tribe.start_wake_time, m.target_wake_time), (dt.time(6), dt.time(5)))
        payload = Notification.objects.get(user=u, kind="approved").payload
        self.assertEqual((payload["alarm"], payload["target"], payload["name"]), ("06:00", "05:00", "Ali"))

    def test_closed_slot_and_bad_input_rejected(self):
        self.slot.is_open = False
        self.slot.save()
        with self.assertRaises(services.RuleError):
            self.apply(11)
        with self.assertRaises(services.RuleError):
            services.register_user(telegram_id=12, gender="M", goal="x", region="mars")
        with self.assertRaises(services.RuleError):
            services.register_user(telegram_id=13, gender="M", goal="x", first_name="A")

    def test_countdown_and_upcoming(self):
        u = self.apply(10)
        services.approve_user(u)
        today = MONDAY - dt.timedelta(days=3)
        rows = services.countdown_list(today)
        self.assertEqual((rows[0]["telegram_id"], rows[0]["days_left"], rows[0]["alarm"]), (10, 3, "06:00"))
        self.assertIsNotNone(services.upcoming_membership(u))

    def test_award_on_stage_and_images_render(self):
        m = self.make_member(1)
        for i in range(3):
            day = MONDAY + dt.timedelta(days=i)
            self.complete_morning(m, day)
            services.evaluate_day(services.ensure_day_record(m, day))
        award = m.awards.get()
        self.assertEqual(award.stage.day, 3)
        n = Notification.objects.get(user=m.user, kind="stage_up")
        self.assertEqual((n.payload["award_id"], n.payload["rank"]), (award.id, "Oddiy askar"))
        from apps.camp.awards import render_award, render_preview
        from apps.control.models import Stage
        self.assertTrue(render_award(award).startswith(PNG))
        for stage in Stage.objects.all():
            self.assertTrue(render_preview(stage).startswith(PNG))
        # Takroriy chaqiruv ikkinchi mukofot bermaydi
        services.grant_award(m, rules.stage_for(3))
        self.assertEqual(m.awards.count(), 1)

    def test_invite_image_renders(self):
        from apps.accounts.manifest import render_manifest
        self.assertTrue(render_manifest(self.apply(10)).startswith(PNG))

    def test_clone_cohort_next_week(self):
        new = services.clone_cohort(self.cohort)
        self.assertEqual(new.start_date, self.cohort.start_date + dt.timedelta(days=7))
        self.assertEqual(new.slots.get().start_wake_time, dt.time(6))

    def test_bot_messages_follow_new_defaults_unless_customized(self):
        BotMessage.objects.filter(key="guide").update(text="eski standart")  # admin o'zgartirmagan holat
        custom = BotMessage.objects.get(key="rules")
        custom.text = "Bizning nizom"
        custom.save()
        BotMessage.sync_defaults()
        guide = BotMessage.objects.get(key="guide")
        self.assertEqual(guide.text, guide.default_text)
        self.assertEqual(BotMessage.objects.get(key="rules").text, "Bizning nizom")


@override_settings(BOT_API_SECRET="s3cret")
class BotSlotsApiTests(CampTestCase):
    def test_bot_flow_slots_register_practice(self):
        self.cohort.status = Cohort.Status.RECRUITING
        self.cohort.save()
        WakeSlot.objects.create(cohort=self.cohort, start_wake_time=dt.time(6), target_wake_time=dt.time(5))
        client = APIClient()
        client.credentials(HTTP_X_BOT_SECRET="s3cret")
        slots = client.get("/api/bot/slots/").json()
        self.assertEqual(slots[0]["start_wake_time"], "06:00")
        client.post("/api/bot/users/register/", {
            "telegram_id": 20, "gender": "F", "goal": "Erta turish", "first_name": "Laylo", "last_name": "Karimova",
            "region": "fergana", "slot_id": slots[0]["id"],
        }, format="json")
        user = client.post("/api/bot/users/20/approve/").json()
        self.assertEqual(user["upcoming"]["alarm"], "06:00")
        practice = client.post("/api/bot/voice/", {"telegram_id": 20, "file_id": "f"}, format="json").json()
        self.assertTrue(practice["practice"])
        self.assertEqual(len(client.get("/api/bot/countdown/").json()), 1)
        self.assertIn("regions", client.get("/api/bot/config/").json())
