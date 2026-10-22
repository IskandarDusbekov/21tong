import { useState } from "react";
import { CircleUserRound, LogOut, MessagesSquare, Sun, Sunrise, Target, Trophy, Wrench } from "lucide-react";
import { api, devUser, inTelegram } from "./api.js";
import { ToastProvider, useLoad } from "./ui.jsx";
import Bounties from "./screens/Bounties.jsx";
import Chat from "./screens/Chat.jsx";
import DevLogin from "./screens/DevLogin.jsx";
import Profile from "./screens/Profile.jsx";
import Rating from "./screens/Rating.jsx";
import Today from "./screens/Today.jsx";

// Faqat `npm run dev` da true — production build'da (`npm run build`) false.
// Shuning uchun dev kirish ekrani haqiqiy saytda hech qachon ko'rinmaydi.
const DEV = import.meta.env.DEV;

const TABS = [
  { id: "today", label: "Bugun", icon: Sun },
  { id: "chat", label: "Rota", icon: MessagesSquare },
  { id: "bounty", label: "Bounty", icon: Target },
  { id: "rating", label: "Reyting", icon: Trophy },
  { id: "profile", label: "Profil", icon: CircleUserRound },
];

function Main({ dev, onLogout }) {
  const [tab, setTab] = useState("today");
  const { data: me, error, reload } = useLoad(api.me);

  const go = (id) => {
    setTab(id);
    window.scrollTo({ top: 0 });
    if (id === "today" || id === "profile") reload();
  };

  return (
    <div className="app">
      {dev && (
        <div className="devbar">
          <span><Wrench size={14} />Dev: <b>{dev.name}</b> · {dev.gender === "F" ? "qiz" : "yigit"}</span>
          <button className="btn btn-soft" style={{ padding: "5px 10px", fontSize: 13 }} onClick={onLogout}>
            <LogOut size={14} /> Almashtirish
          </button>
        </div>
      )}
      <main>
        {tab === "today" && <Today me={me} error={error} reload={reload} />}
        {tab === "chat" && <Chat me={me} />}
        {tab === "bounty" && <Bounties me={me} reloadMe={reload} />}
        {tab === "rating" && <Rating />}
        {tab === "profile" && <Profile me={me} error={error} />}
      </main>
      <nav className="tabbar">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} className={tab === id ? "active" : ""} onClick={() => go(id)} aria-current={tab === id ? "page" : undefined}>
            <Icon size={21} strokeWidth={tab === id ? 2.4 : 2} />
            {label}
          </button>
        ))}
      </nav>
    </div>
  );
}

/** Ilova Telegram tashqarisida (oddiy brauzerda) ochilganda — botga yo'naltiruvchi ekran. */
function OpenInTelegram() {
  return (
    <div className="app">
      <main style={{ display: "flex", minHeight: "70vh", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div style={{ textAlign: "center", maxWidth: 320 }}>
          <div style={{
            width: 56, height: 56, margin: "0 auto 16px", borderRadius: 16, display: "grid", placeItems: "center",
            background: "linear-gradient(135deg, var(--sun-2), var(--sun))",
          }}>
            <Sunrise size={28} color="#fff" />
          </div>
          <h2 style={{ margin: "0 0 8px" }}>21 Tong</h2>
          <p style={{ color: "var(--muted)", lineHeight: 1.5, margin: 0 }}>
            Bu ilova Telegram ichida ishlaydi. Botni oching va pastdagi <b>«Menu»</b> tugmasini bosing.
          </p>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const [dev, setDev] = useState(() => (inTelegram || !DEV ? null : devUser.get()));

  if (inTelegram) return <ToastProvider><Main /></ToastProvider>;
  if (!DEV) return <ToastProvider><OpenInTelegram /></ToastProvider>;

  return (
    <ToastProvider>
      {dev ? (
        <Main key={dev.telegram_id} dev={dev} onLogout={() => { devUser.clear(); setDev(null); }} />
      ) : (
        <DevLogin onPick={(u) => { devUser.set(u); setDev(u); }} />
      )}
    </ToastProvider>
  );
}
