// Panel API: sessiya (cookie) + CSRF. Barcha so'rovlar /api/panel/* ga.
let csrfToken = "";

function cookie(name) {
  return document.cookie.split("; ").find((c) => c.startsWith(name + "="))?.split("=")[1] || "";
}

function errorText(data) {
  if (!data) return "Xatolik yuz berdi";
  if (typeof data === "string") return data;
  if (data.detail) return Array.isArray(data.detail) ? data.detail.join(" ") : data.detail;
  return Object.entries(data)
    .map(([k, v]) => `${k === "non_field_errors" ? "" : k + ": "}${Array.isArray(v) ? v.join(" ") : v}`)
    .join("; ");
}

export async function request(path, { method = "GET", body, query } = {}) {
  const qs = query ? "?" + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== "" && v != null)) : "";
  const res = await fetch(`/api/panel${path}${qs}`, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(method !== "GET" && { "X-CSRFToken": csrfToken || cookie("csrftoken") }),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(errorText(data));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  session: async () => {
    const d = await request("/session/");
    csrfToken = d.csrf;
    return d.user;
  },
  login: async (username, password) => {
    const d = await request("/session/", { method: "POST", body: { username, password } });
    csrfToken = d.csrf;
    return d.user;
  },
  logout: () => request("/session/", { method: "DELETE" }),

  dashboard: () => request("/dashboard/"),
  applications: (status) => request("/applications/", { query: { status } }),
  decide: (id, decision) => request(`/applications/${id}/${decision}/`, { method: "POST" }),
  members: (query) => request("/members/", { query }),
  member: (id) => request(`/members/${id}/`),
  memberAction: (id, body) => request(`/members/${id}/action/`, { method: "POST", body }),
  squads: (query) => request("/squads/", { query }),
  videos: (status) => request("/videos/", { query: { status } }),
  videoDecide: (id, decision) => request(`/videos/${id}/${decision}/`, { method: "POST" }),

  cohorts: () => request("/cohorts/"),
  createCohort: (body) => request("/cohorts/", { method: "POST", body }),
  updateCohort: (id, body) => request(`/cohorts/${id}/`, { method: "PATCH", body }),
  cohortAction: (id, action) => request(`/cohorts/${id}/action/`, { method: "POST", body: { action } }),

  settings: () => request("/settings/"),
  saveSettings: (body) => request("/settings/", { method: "PUT", body }),
  messages: () => request("/messages/"),
  saveMessage: (key, text) => request(`/messages/${key}/`, { method: "PUT", body: { text } }),
  resetMessage: (key) => request(`/messages/${key}/`, { method: "DELETE" }),

  phrases: () => request("/phrases/"),
  addPhrase: (text) => request("/phrases/", { method: "POST", body: { text } }),
  updatePhrase: (id, body) => request(`/phrases/${id}/`, { method: "PATCH", body }),
  deletePhrase: (id) => request(`/phrases/${id}/`, { method: "DELETE" }),
  stages: () => request("/stages/"),
  stageIcons: () => request("/stages/icons/"),
  addStage: (body) => request("/stages/", { method: "POST", body }),
  updateStage: (id, body) => request(`/stages/${id}/`, { method: "PATCH", body }),
  deleteStage: (id) => request(`/stages/${id}/`, { method: "DELETE" }),

  broadcasts: () => request("/broadcasts/"),
  previewBroadcast: (body) => request("/broadcasts/", { method: "POST", body, query: { preview: 1 } }),
  sendBroadcast: (body) => request("/broadcasts/", { method: "POST", body }),
};
