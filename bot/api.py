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

    async def get_user(self, telegram_id):
        try:
            return (await self._request("GET", f"/users/{telegram_id}/")).json()
        except ApiError as e:
            if e.status == 404:
                return None
            raise

    async def register(self, **data):
        return (await self._request("POST", "/users/register/", json=data)).json()

    async def manifest(self, telegram_id) -> bytes:
        return (await self._request("GET", f"/users/{telegram_id}/manifest.png")).content

    async def recruiting_cohorts(self):
        return (await self._request("GET", "/cohorts/recruiting/")).json()

    async def join(self, **data):
        return (await self._request("POST", "/join/", json=data)).json()

    async def voice(self, telegram_id, chat_id):
        return (await self._request("POST", "/voice/", json={"telegram_id": telegram_id, "chat_id": chat_id})).json()

    async def video(self, telegram_id, file_id, duration):
        return (await self._request(
            "POST", "/video/", json={"telegram_id": telegram_id, "file_id": file_id, "duration": duration}
        )).json()

    async def vote(self, review_id, telegram_id, approved):
        return (await self._request(
            "POST", f"/reviews/{review_id}/vote/", json={"telegram_id": telegram_id, "approved": approved}
        )).json()

    async def notifications(self):
        return (await self._request("GET", "/notifications/")).json()

    async def ack(self, ids):
        await self._request("POST", "/notifications/ack/", json={"ids": ids})

    async def alarms(self, hhmm):
        return (await self._request("GET", "/alarms/", params={"time": hhmm})).json()

    async def windows(self):
        return (await self._request("GET", "/windows/")).json()


backend = Backend()
