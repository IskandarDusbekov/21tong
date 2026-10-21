// Backend bilan aloqa. Telegram ichida har so'rovga imzolangan initData qo'shiladi;
// oddiy brauzerda (lokal ishlab chiqish) — tanlangan demo foydalanuvchining telegram_id si.
const BASE = (import.meta.env.VITE_API_URL || "") + "/api/app";
const DEV_KEY = "21tong.devUser";

export const tg = window.Telegram?.WebApp;
export const inTelegram = Boolean(tg?.initData);

export const devUser = {
  get() {
    try {
      return JSON.parse(localStorage.getItem(DEV_KEY));
    } catch {
      return null;
    }
  },
  set(user) {
    try {
      localStorage.setItem(DEV_KEY, JSON.stringify(user));
    } catch {
      /* private rejim — sessiya davomida qayta tanlanadi */
    }
  },
  clear() {
    try {
      localStorage.removeItem(DEV_KEY);
    } catch {
      /* e'tiborsiz */
    }
  },
};

function authHeader() {
  if (inTelegram) return `tma ${tg.initData}`;
  const dev = devUser.get();
  return dev ? `dev ${dev.telegram_id}` : "";
}

async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", Authorization: authHeader() },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Xatolik yuz berdi");
  return data;
}

/** Mukofot rasmi: <img> sarlavha yubora olmaydi, shuning uchun blob URL qilib olamiz. */
export async function awardImage(id) {
  const res = await fetch(`${BASE}/awards/${id}.png`, { headers: { Authorization: authHeader() } });
  if (!res.ok) throw new Error("Rasm yuklanmadi");
  return URL.createObjectURL(await res.blob());
}

/** Raport media'si (ovoz/video): <audio>/<video> sarlavha yubora olmaydi — blob URL qilamiz. */
export async function proofMedia(kind, id) {
  const res = await fetch(`${BASE}/media/${kind}/${id}/`, { headers: { Authorization: authHeader() } });
  if (!res.ok) throw new Error("Media yuklanmadi");
  return URL.createObjectURL(await res.blob());
}

/** Chelenj rasmi — <img> sarlavha yubora olmaydi, blob URL qilamiz. */
export async function photoImage(id) {
  const res = await fetch(`${BASE}/photos/${id}.jpg`, { headers: { Authorization: authHeader() } });
  if (!res.ok) throw new Error("Rasm yuklanmadi");
  return URL.createObjectURL(await res.blob());
}

/** Rasm yuklash — multipart (JSON emas). */
export async function uploadPhoto(file) {
  const form = new FormData();
  form.append("image", file);
  const res = await fetch(`${BASE}/photos/`, { method: "POST", headers: { Authorization: authHeader() }, body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Rasm yuborilmadi");
  return data;
}

export const api = {
  me: () => request("/me/"),
  wake: () => request("/wake/", { method: "POST" }),
  squad: () => request("/squad/"),
  chat: () => request("/chat/"),
  sendMessage: (text) => request("/chat/", { method: "POST", body: { text } }),
  freeze: (reason) => request("/freeze/", { method: "POST", body: { reason } }),
  feed: () => request("/feed/"),
  reflect: (text) => request("/feed/", { method: "POST", body: { text } }),
  fire: (id) => request(`/reflections/${id}/fire/`, { method: "POST" }),
  bounties: () => request("/bounties/"),
  completeBounty: (id) => request(`/bounties/${id}/complete/`, { method: "POST" }),
  photos: () => request("/photos/"),
  votePhoto: (id) => request(`/photos/${id}/vote/`, { method: "POST" }),
  ranking: () => request("/leaderboard/"),
  devUsers: () => request("/dev/users/"),
};
