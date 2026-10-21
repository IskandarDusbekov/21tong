// Oddiy hash-router: #/members?squad=3
export function go(page, params) {
  const qs = params ? "?" + new URLSearchParams(params) : "";
  window.location.hash = `/${page}${qs}`;
}

export function parseHash(pages, fallback) {
  const [path, qs] = window.location.hash.replace(/^#\/?/, "").split("?");
  return { page: pages[path] ? path : fallback, params: Object.fromEntries(new URLSearchParams(qs || "")) };
}
