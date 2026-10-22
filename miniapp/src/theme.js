// Light/night rejim. "" — avtomatik (Telegram yoki tizim mavzusiga ergashadi),
// "light" / "dark" — foydalanuvchi o'zi tanlagan (Telegram mavzusidan ustun). localStorage'da saqlanadi.
const KEY = "21tong.theme";

export function getTheme() {
  try {
    return localStorage.getItem(KEY) || "";
  } catch {
    return "";
  }
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme) root.dataset.theme = theme;
  else delete root.dataset.theme;
}

export function setTheme(theme) {
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* private rejim — sessiya davomida ishlaydi */
  }
  applyTheme(theme);
}
