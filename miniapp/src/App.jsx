import { useState } from "react";
import { MessagesSquare, Route, Sun, Sunrise, Target, Trophy } from "lucide-react";
import { api, inTelegram } from "./api.js";
import { SoundToggle, ToastProvider, useLoad } from "./ui.jsx";
import Bounties from "./screens/Bounties.jsx";
import Chat from "./screens/Chat.jsx";
import Journey from "./screens/Journey.jsx";
import Rating from "./screens/Rating.jsx";
import Today from "./screens/Today.jsx";

const TABS = [
  { id: "today", label: "Bugun", icon: Sun },
  { id: "chat", label: "Rota", icon: MessagesSquare },
  { id: "journey", label: "Yo'l", icon: Route },
  { id: "bounty", label: "Bounty", icon: Target },
  { id: "rating", label: "Reyting", icon: Trophy },
];

function Main() {
  const [tab, setTab] = useState("today");
  const { data: me, error, reload } = useLoad(api.me);

  const go = (id) => {
    setTab(id);
    window.scrollTo({ top: 0 });
    if (id === "today" || id === "journey") reload();
  };

  return (
    <div className="app">
      <SoundToggle />
      <main>
        {tab === "today" && <Today me={me} error={error} reload={reload} />}
        {tab === "chat" && <Chat me={me} />}
        {tab === "journey" && <Journey me={me} error={error} />}
        {tab === "bounty" && <Bounties me={me} reloadMe={reload} />}
        {tab === "rating" && <Rating />}
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
            background: "linear-gradient(135deg, #f59e0b, #ef4444)",
          }}>
            <Sunrise size={28} color="#fff" />
          </div>
          <h2 style={{ margin: "0 0 8px" }}>21 Tong</h2>
          <p style={{ color: "var(--muted, #8a8f98)", lineHeight: 1.5, margin: 0 }}>
            Bu ilova Telegram ichida ishlaydi. Botni oching va pastdagi <b>«Menu»</b> tugmasini bosing.
          </p>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return <ToastProvider>{inTelegram ? <Main /> : <OpenInTelegram />}</ToastProvider>;
}
