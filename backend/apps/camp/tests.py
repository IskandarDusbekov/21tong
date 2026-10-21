import datetime as dt
import hashlib
import hmac
import json
import time
from unittest import mock
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.auth import validate_init_data
from apps.accounts.models import User
from apps.camp import rules, services
from apps.camp.models import Cohort, DayRecord, Joker, Membership, Notification, Strike
from apps.community import services as community
from apps.proofs import services as proofs
from apps.proofs.models import VideoProof

TZ = ZoneInfo("Asia/Tashkent")
MONDAY = dt.date(2026, 11, 2)


def at(date, h, m=0):
    return dt.datetime.combine(date, dt.time(h, m), tzinfo=TZ)


class RulesTests(TestCase):
    def test_kaizen_shift(self):
        start, target = dt.time(7, 0), dt.time(5, 30)
        self.assertEqual(rules.alarm_time_for_day(start, target, 1), dt.time(7, 0))
        self.assertEqual(rules.alarm_time_for_day(start, target, 6), dt.time(7, 0))
        self.assertEqual(rules.alarm_time_for_day(start, target, 7), dt.time(6, 55))
        self.assertEqual(rules.alarm_time_for_day(start, target, 8), dt.time(6, 50))
        self.assertEqual(rules.alarm_time_for_day(start, target, 21), dt.time(5, 45))
        self.assertEqual(rules.alarm_time_for_day(start, target, 30), dt.time(5, 30))

    def test_threshold(self):
        self.assertEqual(rules.approval_threshold(3), 2)
        self.assertEqual(rules.approval_threshold(2), 2)
        self.assertEqual(rules.approval_threshold(1), 1)

    def test_stage(self):
        self.assertIsNone(rules.stage_for(2))
        self.assertEqual(rules.stage_for(3)["code"], "survivor")
        self.assertEqual(rules.stage_for(21)["code"], "iron_will")


class CampTestCase(TestCase):
    def setUp(self):
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

    def complete_morning(self, m, date, video=True):
        alarm = services.ensure_day_record(m, date).alarm_time
        services.press_wake(m, at(date, alarm.hour, alarm.minute))
        services.record_voice(m, at(date, 7, 1))
        if video:
            return proofs.submit_video(m, f"file-{m.id}-{date}", 10, at(date, 7, 3))


class OnboardingTests(CampTestCase):
    def test_gender_cannot_change(self):
        services.register_user(telegram_id=1, gender="F", goal="x")
        with self.assertRaises(services.RuleError):
            services.register_user(telegram_id=1, gender="M", goal="x")

    def test_referral_joker_given_once_on_friend_approval(self):
        a = services.register_user(telegram_id=1, gender="M", goal="x")
        b = services.register_user(telegram_id=2, gender="M", goal="x", referral_code=a.referral_code)
        c = services.register_user(telegram_id=3, gender="F", goal="x", referral_code=a.referral_code)
        self.assertEqual(services.jokers_available(a), 0)
        services.approve_user(b)
        services.approve_user(c)
        self.assertEqual(services.jokers_available(a), 1)

    def test_tribes_split_by_gender(self):
        boy = self.make_member(1, "M")
        girl = self.make_member(2, "F")
        self.assertNotEqual(boy.tribe_id, girl.tribe_id)
        self.assertEqual(boy.tribe.start_wake_time, girl.tribe.start_wake_time)


class ReviewTests(CampTestCase):
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
        proof = self.complete_morning(members[0], MONDAY)
        reviews = list(proof.reviews.select_related("reviewer"))
        proofs.cast_vote(reviews[0], reviews[0].reviewer, True)
        proof.refresh_from_db()
        self.assertEqual(proof.status, VideoProof.Status.REVIEWING)
        proofs.cast_vote(reviews[1], reviews[1].reviewer, True)
        proof.refresh_from_db()
        self.assertEqual(proof.status, VideoProof.Status.APPROVED)

    def test_cannot_vote_on_others_review(self):
        members = [self.make_member(i) for i in range(1, 5)]
        proof = self.complete_morning(members[0], MONDAY)
        review = proof.reviews.first()
        with self.assertRaises(services.RuleError):
            proofs.cast_vote(review, members[0], True)


class EvaluationTests(CampTestCase):
    def evaluate(self, m, date):
        return services.evaluate_day(services.ensure_day_record(m, date))

    def test_completed_day(self):
        m = self.make_member(1)
        self.complete_morning(m, MONDAY, video=False)
        self.assertEqual(self.evaluate(m, MONDAY).status, DayRecord.Status.COMPLETED)

    def test_late_wake_gives_strike(self):
        m = self.make_member(1)
        services.press_wake(m, at(MONDAY, 7, 20))
        services.record_voice(m, at(MONDAY, 7, 21))
        record = self.evaluate(m, MONDAY)
        self.assertEqual(record.status, DayRecord.Status.FAILED)
        self.assertEqual(m.strikes.get().reason, Strike.Reason.LATE)

    def test_missing_video_after_day7(self):
        m = self.make_member(1)
        day8 = MONDAY + dt.timedelta(days=7)  # 7-kun yakshanba, shuning uchun 8-kun (dushanba)
        self.complete_morning(m, day8, video=False)
        self.evaluate(m, day8)
        self.assertEqual(m.strikes.get().reason, Strike.Reason.NO_VIDEO)

    def test_three_strikes_out(self):
        m = self.make_member(1)
        for i in range(3):
            self.evaluate(m, MONDAY + dt.timedelta(days=i))
        m.refresh_from_db()
        self.assertEqual(m.status, Membership.Status.EXPELLED)
        self.assertTrue(Notification.objects.filter(user=m.user, kind="expelled").exists())

    def test_joker_cancels_strike(self):
        m = self.make_member(1)
        Joker.objects.create(user=m.user, source=Joker.Source.ADMIN)
        for i in range(3):
            self.evaluate(m, MONDAY + dt.timedelta(days=i))
        m.refresh_from_db()
        self.assertEqual(m.status, Membership.Status.ACTIVE)
        self.assertEqual(m.active_strikes, 2)

    def test_sunday_rest_and_joker(self):
        sleeper, early = self.make_member(1), self.make_member(2)
        sunday = MONDAY + dt.timedelta(days=6)
        self.complete_morning(early, sunday)
        self.assertEqual(self.evaluate(sleeper, sunday).status, DayRecord.Status.REST)
        self.assertEqual(self.evaluate(early, sunday).status, DayRecord.Status.COMPLETED)
        self.assertEqual(sleeper.strikes.count(), 0)
        self.assertEqual(services.jokers_available(early.user), 1)

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

    def test_dev_login_only_when_enabled(self):
        self.make_member(42)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="dev 42")
        with override_settings(DEV_LOGIN=True):
            self.assertEqual(client.get("/api/app/me/").status_code, 200)
        with override_settings(DEV_LOGIN=False):
            self.assertIn(client.get("/api/app/me/").status_code, (401, 403))
            self.assertEqual(client.get("/api/app/dev/users/").status_code, 404)

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
