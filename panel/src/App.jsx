import { useCallback, useEffect, useState } from "react";
import {
  CalendarRange, FileText, Home, Inbox, LogOut, Megaphone, Menu, MessagesSquare, MessageSquareText, Moon,
  Settings2, Sun, Sunrise, Target, Users, UsersRound, Video,
} from "lucide-react";
import { api } from "./api.js";
import { go, parseHash } from "./router.js";
import { Avatar, ConfirmProvider, ToastProvider } from "./ui.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Applications from "./pages/Applications.jsx";
import Members from "./pages/Members.jsx";
import Squads from "./pages/Squads.jsx";
import Videos from "./pages/Videos.jsx";
import Chats from "./pages/Chats.jsx";
import Cohorts from "./pages/Cohorts.jsx";
import Bounties from "./pages/Bounties.jsx";
import Broadcast from "./pages/Broadcast.jsx";
import SettingsPage from "./pages/Settings.jsx";
import Messages from "./pages/Messages.jsx";
import Content from "./pages/Content.jsx";

const NAV = [
  { label: "Asosiy", items: [
    { id: "dashboard", title: "Bosh sahifa", icon: Home, page: Dashboard },
    { id: "applications", title: "Arizalar", icon: Inbox, page: Applications, badge: "pending_applications" },
    { id: "members", title: "Ishtirokchilar", icon: Users, page: Members },
    { id: "squads", title: "Rotalar", icon: UsersRound, page: Squads },
    { id: "videos", title: "Video raportlar", icon: Video, page: Videos, badge: "videos_reviewing" },
    { id: "chats", title: "Rota chatlari", icon: MessagesSquare, page: Chats },
  ] },
  { label: "Lager", items: [
    { id: "cohorts", title: "Oqimlar", icon: CalendarRange, page: Cohorts },
    { id: "bounties", title: "Topshiriqlar (Bounty)", icon: Target, page: Bounties },
    { id: "broadcast", title: "Ommaviy xabar", icon: Megaphone, page: Broadcast },
  ] },
  { label: "Sozlash", items: [
    { id: "settings", title: "Lager qoidalari", icon: Settings2, page: SettingsPage },
    { id: "messages", title: "Bot matnlari", icon: MessageSquareText, page: Messages },
    { id: "content", title: "Gaplar va bosqichlar", icon: FileText, page: Content },
  ] },
];
const PAGES = Object.fromEntries(NAV.flatMap((g) => g.items).map((i) => [i.id, i]));

function useRoute() {
  const [route, setRoute] = useState(() => parseHash(PAGES, "dashboard"));
  useEffect(() => {
    const on = () => { setRoute(parseHash(PAGES, "dashboard")); window.scrollTo({ top: 0 }); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem("panel.theme") || ""; } catch { return ""; }
  });
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
    try { localStorage.setItem("panel.theme", theme); } catch { /* e'tiborsiz */ }
  }, [theme]);
  const dark = theme ? theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  return [dark, () => setTheme(dark ? "light" : "dark")];
}

function Shell({ user, onLogout }) {
  const route = useRoute();
  const [open, setOpen] = useState(false);
  const [counts, setCounts] = useState({});
  const [dark, toggleTheme] = useTheme();

  const refreshCounts = useCallback(() => {
    api.dashboard().then((d) => setCounts(d.kpis)).catch(() => {});
  }, []);
  useEffect(() => {
    refreshCounts();
    const t = setInterval(refreshCounts, 60000);
    return () => clearInterval(t);
  }, [refreshCounts, route.page]);

  const current = PAGES[route.page];
  const Page = current.page;

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Sunrise size={20} color="#fff" /></div>
          <div><b>21 Tong</b><small>Qo'mondonlik paneli</small></div>
        </div>
        {NAV.map((g) => (
          <div key={g.label} className="nav-group">
            <div className="nav-label">{g.label}</div>
            {g.items.map((item) => (
              <button
                key={item.id} className={`nav-item ${route.page === item.id ? "active" : ""}`}
                onClick={() => { go(item.id); setOpen(false); }}
              >
                <item.icon size={18} />
                {item.title}
                {item.badge && counts[item.badge] > 0 && <span className="badge-count">{counts[item.badge]}</span>}
              </button>
            ))}
          </div>
        ))}
        <div className="sidebar-foot">
          <div className="user-chip">
            <Avatar name={user.name} />
            <div style={{ minWidth: 0 }}><b>{user.name}</b><small style={{ color: "var(--night-muted)" }}>Admin</small></div>
            <button className="btn btn-ghost btn-icon" onClick={toggleTheme} title="Mavzu" aria-label="Mavzuni almashtirish">
              {dark ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button className="btn btn-ghost btn-icon" onClick={onLogout} title="Chiqish" aria-label="Chiqish"><LogOut size={17} /></button>
          </div>
        </div>
      </aside>
      {open && <div className="backdrop" style={{ zIndex: 44 }} onClick={() => setOpen(false)} />}

      <div className="main">
        <header className="topbar">
          <button className="btn btn-ghost btn-icon" onClick={() => setOpen(true)} aria-label="Menyu"><Menu size={20} /></button>
          <b>{current.title}</b>
        </header>
        <main className="page">
          <Page key={route.page} params={route.params} onChange={refreshCounts} />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(undefined);
  useEffect(() => { api.session().then(setUser).catch(() => setUser(null)); }, []);

  const logout = async () => {
    await api.logout().catch(() => {});
    await api.session().catch(() => {});
    setUser(null);
  };

  return (
    <ToastProvider>
      <ConfirmProvider>
        {user === undefined ? null : user ? <Shell user={user} onLogout={logout} /> : <Login onLogin={setUser} />}
      </ConfirmProvider>
    </ToastProvider>
  );
}
