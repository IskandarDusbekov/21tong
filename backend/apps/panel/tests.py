import datetime as dt

from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.camp import services
from apps.camp.models import Cohort, Membership
from apps.camp.tests import MONDAY, CampTestCase
from apps.control.models import BotMessage, CampSettings, Phrase


class PanelTestCase(CampTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.staff = User.objects.create_user("boss", password="test-pass-123", is_staff=True)
        self.client.force_authenticate(self.staff)


class PanelAuthTests(CampTestCase):
    def test_login_flow_and_staff_only(self):
        User.objects.create_user("boss", password="test-pass-123", is_staff=True)
        User.objects.create_user("oddiy", password="test-pass-123")
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get("/api/panel/session/").json()["csrf"]
        self.assertEqual(client.get("/api/panel/dashboard/").status_code, 403)
        bad = client.post("/api/panel/session/", {"username": "oddiy", "password": "test-pass-123"},
                          format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(bad.status_code, 403)
        ok = client.post("/api/panel/session/", {"username": "boss", "password": "test-pass-123"},
                         format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(ok.json()["user"]["username"], "boss")
        self.assertEqual(client.get("/api/panel/dashboard/").status_code, 200)


class PanelDataTests(PanelTestCase):
    def test_dashboard(self):
        m = self.make_member(1)
        self.complete_morning(m, MONDAY)
        services.evaluate_day(services.ensure_day_record(m, MONDAY))
        data = self.client.get("/api/panel/dashboard/").json()
        self.assertEqual(data["kpis"]["active"], 1)
        self.assertEqual(data["cohorts"][0]["series"][0]["done"], 1)
        self.assertEqual(len(data["squads"]), 1)

    def test_applications_approve(self):
        u = services.register_user(telegram_id=5, gender="M", goal="Erta turish",
                                   current_wake_time=dt.time(7), target_wake_time=dt.time(6))
        items = self.client.get("/api/panel/applications/").json()["items"]
        self.assertEqual(items[0]["id"], u.id)
        self.cohort.status = Cohort.Status.RECRUITING
        self.cohort.save()
        resp = self.client.post(f"/api/panel/applications/{u.id}/approve/").json()
        self.assertEqual(resp["status"], "approved")
        self.assertIn("1-rota", resp["placed"])
        self.assertEqual(self.client.post(f"/api/panel/applications/{u.id}/approve/").status_code, 400)

    def test_members_filter_detail_actions(self):
        boy, girl = self.make_member(1, "M"), self.make_member(2, "F")
        rows = self.client.get("/api/panel/members/", {"gender": "F"}).json()["items"]
        self.assertEqual([r["id"] for r in rows], [girl.id])
        detail = self.client.get(f"/api/panel/members/{boy.id}/").json()
        self.assertEqual(len(detail["journey"]["days"]), 21)

        url = f"/api/panel/members/{boy.id}/action/"
        self.client.post(url, {"action": "give_immunity"}, format="json")
        self.client.post(url, {"action": "give_strike"}, format="json")
        strike_id = self.client.get(f"/api/panel/members/{boy.id}/").json()["strikes_list"][0]["id"]
        self.client.post(url, {"action": "revoke_strike", "strike_id": strike_id}, format="json")
        self.client.post(url, {"action": "expel"}, format="json")
        boy.refresh_from_db()
        self.assertEqual((boy.status, boy.active_strikes), (Membership.Status.EXPELLED, 0))
        self.assertEqual(services.immunities_available(boy.user), 1)
        self.assertEqual(self.client.post(url, {"action": "nimadir"}, format="json").status_code, 400)

    def test_settings_update_and_validation(self):
        data = self.client.get("/api/panel/settings/").json()
        self.assertEqual(data["groups"][0]["fields"][0]["name"], "wake_grace_minutes")
        resp = self.client.put("/api/panel/settings/", {"voice_deadline_minutes": 9, "sunday_rest": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        cache.clear()
        c = CampSettings.load()
        self.assertEqual((c.voice_deadline_minutes, c.sunday_rest), (9, False))
        bad = self.client.put("/api/panel/settings/", {"max_strikes": 0}, format="json")
        self.assertEqual(bad.status_code, 400)
        bad = self.client.put("/api/panel/settings/", {"default_morning_start": "08:00", "default_morning_end": "07:00"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_messages_edit_validate_reset(self):
        resp = self.client.put("/api/panel/messages/voice_ok/", {"text": "Zo'r! {day}-kun"}, format="json")
        self.assertTrue(resp.json()["changed"])
        bad = self.client.put("/api/panel/messages/voice_ok/", {"text": "{yoq}"}, format="json")
        self.assertEqual(bad.status_code, 400)
        reset = self.client.delete("/api/panel/messages/voice_ok/").json()
        self.assertFalse(reset["changed"])
        self.assertEqual(BotMessage.objects.get(key="voice_ok").text, reset["default"])

    def test_phrases_crud(self):
        before = Phrase.objects.count()
        p = self.client.post("/api/panel/phrases/", {"text": "Yangi gap"}, format="json").json()
        self.client.patch(f"/api/panel/phrases/{p['id']}/", {"is_active": False}, format="json")
        self.assertFalse(Phrase.objects.get(pk=p["id"]).is_active)
        self.client.delete(f"/api/panel/phrases/{p['id']}/")
        self.assertEqual(Phrase.objects.count(), before)

    def test_cohort_create_and_actions(self):
        resp = self.client.post("/api/panel/cohorts/", {"name": "2-oqim", "start_date": "2026-12-01"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        cid = resp.json()["id"]
        self.client.post(f"/api/panel/cohorts/{cid}/action/", {"action": "start"}, format="json")
        self.assertEqual(Cohort.objects.get(pk=cid).status, Cohort.Status.RUNNING)

    def test_broadcast_preview_and_send(self):
        self.make_member(1, "M")
        self.make_member(2, "F")
        body = {"text": "Diqqat!", "audience": "active", "gender": "F"}
        self.assertEqual(self.client.post("/api/panel/broadcasts/?preview=1", body, format="json").json()["recipients"], 1)
        self.assertEqual(self.client.post("/api/panel/broadcasts/", body, format="json").json()["sent_count"], 1)
        bad = self.client.post("/api/panel/broadcasts/", {"text": "x", "audience": "squad"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_every_endpoint_answers(self):
        self.make_member(1)
        for url in ["dashboard", "applications", "members", "squads", "settings", "messages", "phrases",
                    "stages", "stages/icons", "cohorts", "broadcasts", "videos"]:
            self.assertEqual(self.client.get(f"/api/panel/{url}/").status_code, 200, url)



