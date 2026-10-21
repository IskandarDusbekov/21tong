"""Backend bilan aloqa. Bot hech qanday biznes-qoidani o'zi hal qilmaydi."""
import httpx

import config


class ApiError(Exception):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class Backend:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=f"{config.BACKEND_URL}/api/bot",
            headers={"X-Bot-Secret": config.BOT_API_SECRET},
            timeout=15,
        )

    async def _request(self, method, url, **kwargs):
        resp = await self.client.request(method, url, **kwargs)
        if resp.status_code >= 400:
            try:
                data = resp.json()
                detail = data.get("detail") if isinstance(data, dict) else data
                detail = detail or data
            except ValueError:
                detail = resp.text
            raise ApiError(resp.status_code, detail)
        return resp

    async def _json(self, method, url, **kwargs):
        return (await self._request(method, url, **kwargs)).json()

    # --- foydalanuvchi va ariza ---
    async def get_user(self, telegram_id):
        try:
            return await self._json("GET", f"/users/{telegram_id}/")
        except ApiError as e:
            if e.status == 404:
                return None
            raise

    async def register(self, **data):
        return await self._json("POST", "/users/register/", json=data)

    async def pending(self):
        return await self._json("GET", "/users/pending/")

    async def approve(self, telegram_id):
        return await self._json("POST", f"/users/{telegram_id}/approve/")

    async def reject(self, telegram_id):
        return await self._json("POST", f"/users/{telegram_id}/reject/")

    async def manifest(self, telegram_id) -> bytes:
        return (await self._request("GET", f"/users/{telegram_id}/manifest.png")).content

    async def recruiting_cohorts(self):
        return await self._json("GET", "/cohorts/recruiting/")

    async def join(self, **data):
        return await self._json("POST", "/join/", json=data)

    # --- tonggi zanjir ---
    async def wake(self, telegram_id):
        return await self._json("POST", "/wake/", json={"telegram_id": telegram_id})

    async def voice(self, telegram_id, file_id):
        return await self._json("POST", "/voice/", json={"telegram_id": telegram_id, "file_id": file_id})

    async def video(self, telegram_id, file_id, duration):
        return await self._json(
            "POST", "/video/", json={"telegram_id": telegram_id, "file_id": file_id, "duration": duration}
        )

    async def vote(self, review_id, telegram_id, approved):
        return await self._json(
            "POST", f"/reviews/{review_id}/vote/", json={"telegram_id": telegram_id, "approved": approved}
        )

    # --- navbat va jadval ---
    async def notifications(self):
        return await self._json("GET", "/notifications/")

    async def ack(self, ids):
        await self._request("POST", "/notifications/ack/", json={"ids": ids})

    async def alarms(self, hhmm):
        return await self._json("GET", "/alarms/", params={"time": hhmm})

    async def windows(self):
        return await self._json("GET", "/windows/")

    async def roll_call(self):
        return await self._json("GET", "/roll-call/")

    # --- rota guruhlari ---
    async def squads(self, unlinked=False):
        return await self._json("GET", "/squads/", params={"unlinked": 1} if unlinked else None)

    async def link_squad(self, squad_id, chat_id, invite_link=""):
        return await self._json(
            "POST", f"/squads/{squad_id}/link/", json={"chat_id": chat_id, "invite_link": invite_link}
        )


backend = Backend()
