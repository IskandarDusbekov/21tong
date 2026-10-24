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
        c = Cohort.objects.get(pk=cid)
        self.assertEqual(c.status, Cohort.Status.RUNNING)
        # Qo'lda start — bugundan 1-kun (avval "oqimning oxirgi kuni" xatosi chiqardi)
        today = services.local_now().date()
        self.assertEqual(c.start_date, today)
        self.assertEqual(c.day_number(today), 1)

    def test_cohort_delete_only_when_empty(self):
        cid = self.client.post("/api/panel/cohorts/", {"name": "Xato oqim", "start_date": "2026-12-01"}, format="json").json()["id"]
        self.assertEqual(self.client.delete(f"/api/panel/cohorts/{cid}/").status_code, 204)
        self.assertFalse(Cohort.objects.filter(pk=cid).exists())
        self.make_member(1)  # self.cohort'da ishtirokchi bor
        self.assertEqual(self.client.delete(f"/api/panel/cohorts/{self.cohort.id}/").status_code, 400)
        self.assertTrue(Cohort.objects.filter(pk=self.cohort.id).exists())

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
                    "stages", "stages/icons", "cohorts", "broadcasts", "videos", "bounties", "chats"]:
            self.assertEqual(self.client.get(f"/api/panel/{url}/").status_code, 200, url)

    def test_bounty_create_and_delete(self):
        from apps.community.models import Bounty
        self.make_member(1)
        body = {"cohort": self.cohort.id, "date": services.local_now().date().isoformat(),
                "title": "20 bet kitob", "description": "Ixtiyoriy", "reward": 15}
        bid = self.client.post("/api/panel/bounties/", body, format="json").json()["id"]
        items = self.client.get("/api/panel/bounties/").json()["items"]
        self.assertTrue(any(b["id"] == bid and b["title"] == "20 bet kitob" for b in items))
        self.assertEqual(self.client.delete(f"/api/panel/bounties/{bid}/").status_code, 204)
        self.assertFalse(Bounty.objects.filter(pk=bid).exists())

    def test_chat_monitoring_and_message_delete(self):
        from apps.community import services as community
        from apps.community.models import SquadMessage
        m = self.make_member(1)
        # Chat oynasini ochib, xabar yozamiz
        cohort = m.cohort
        now = services.local_now().replace(hour=cohort.morning_window_start.hour,
                                            minute=cohort.morning_window_start.minute, second=0, microsecond=0)
        community.post_chat_message(m, "Salom rota", now)
        chats = self.client.get("/api/panel/chats/").json()
        row = next(c for c in chats if c["id"] == m.squad_id)
        self.assertEqual(row["count"], 1)
        thread = self.client.get(f"/api/panel/chats/{m.squad_id}/").json()
        self.assertEqual(thread["messages"][0]["text"], "Salom rota")
        msg_id = thread["messages"][0]["id"]
        self.assertEqual(self.client.delete(f"/api/panel/chat-messages/{msg_id}/").status_code, 204)
        self.assertFalse(SquadMessage.objects.filter(pk=msg_id).exists())

    def test_admin_writes_as_mentor_any_time(self):
        from apps.community import services as community
        m = self.make_member(1)
        # Oyna yopiq bo'lsa ham mentor yoza oladi
        resp = self.client.post(f"/api/panel/chats/{m.squad_id}/", {"text": "Ertaga start!"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self.client.post(f"/api/panel/chats/{m.squad_id}/", {"text": " "}, format="json").status_code, 400)
        thread = self.client.get(f"/api/panel/chats/{m.squad_id}/").json()
        self.assertTrue(thread["messages"][0]["mentor"])
        item = next(it for it in community.squad_chat(m)["items"] if it["type"] == "message")
        self.assertTrue(item["mentor"])
        self.assertFalse(item["me"])
        self.assertTrue(item["author"].startswith("Mentor"))





class PanelSlotsAwardsTests(PanelTestCase):
    def test_slots_crud_and_clone(self):
        url = f"/api/panel/cohorts/{self.cohort.id}/slots/"
        slot = self.client.post(url, {"start_wake_time": "06:30", "target_wake_time": "05:30"}, format="json").json()
        self.assertEqual(slot["start_wake_time"], "06:30")
        dup = self.client.post(url, {"start_wake_time": "06:30", "target_wake_time": "05:30"}, format="json")
        self.assertEqual(dup.status_code, 400)
        wrong = self.client.post(url, {"start_wake_time": "05:00", "target_wake_time": "06:00"}, format="json")
        self.assertEqual(wrong.status_code, 400)
        self.client.patch(f"/api/panel/slots/{slot['id']}/", {"is_open": False}, format="json")
        cohorts = self.client.get("/api/panel/cohorts/").json()["items"]
        self.assertFalse(cohorts[0]["slots"][0]["is_open"])
        r = self.client.post(f"/api/panel/cohorts/{self.cohort.id}/action/", {"action": "clone_next"}, format="json").json()
        self.assertEqual(Cohort.objects.get(pk=r["id"]).slots.count(), 1)

    def test_slot_edit_guards_placed_members(self):
        url = f"/api/panel/cohorts/{self.cohort.id}/slots/"
        empty = self.client.post(url, {"start_wake_time": "06:30", "target_wake_time": "05:30"}, format="json").json()
        ok = self.client.patch(f"/api/panel/slots/{empty['id']}/", {"start_wake_time": "06:45"}, format="json")
        self.assertEqual(ok.json()["start_wake_time"], "06:45")  # bo'sh rota — vaqt o'zgaradi
        busy = self.client.post(url, {"start_wake_time": "07:00", "target_wake_time": "05:30"}, format="json").json()
        self.make_member(1)  # 07:00 → 05:30 rotasiga joylashadi
        moved = self.client.patch(f"/api/panel/slots/{busy['id']}/", {"start_wake_time": "07:15"}, format="json")
        self.assertEqual(moved.status_code, 400)
        renamed = self.client.patch(f"/api/panel/slots/{busy['id']}/", {"title": "Erta qushlar"}, format="json")
        self.assertEqual(renamed.json()["title"], "Erta qushlar")

    def test_stage_preview(self):
        from apps.control.models import Stage
        stage = Stage.objects.first()
        resp = self.client.get(f"/api/panel/stages/{stage.id}/preview.png")
        self.assertEqual(resp["Content-Type"], "image/png")
        self.assertIn("award_types", self.client.get("/api/panel/stages/icons/").json())
