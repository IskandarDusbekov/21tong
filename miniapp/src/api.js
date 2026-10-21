// Backend bilan aloqa. Har so'rovga Telegram imzolagan initData qo'shiladi.
const BASE = (import.meta.env.VITE_API_URL || "") + "/api/app";

export const tg = window.Telegram?.WebApp;

async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `tma ${tg?.initData || ""}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Xatolik yuz berdi");
  return data;
}

export const api = {
  me: () => request("/me/"),
  wake: () => request("/wake/", { method: "POST" }),
  freeze: (reason) => request("/freeze/", { method: "POST", body: { reason } }),
  feed: () => request("/feed/"),
  reflect: (text) => request("/feed/", { method: "POST", body: { text } }),
  fire: (id) => request(`/reflections/${id}/fire/`, { method: "POST" }),
  bounties: () => request("/bounties/"),
  completeBounty: (id) => request(`/bounties/${id}/complete/`, { method: "POST" }),
  leaderboard: () => request("/leaderboard/"),
};
