import { useState } from "react";
import { LogOut, MessagesSquare, Route, Sun, Target, Trophy, Wrench } from "lucide-react";
import { api, devUser, inTelegram } from "./api.js";
import { SoundToggle, ToastProvider, useLoad } from "./ui.jsx";
import Bounties from "./screens/Bounties.jsx";
import Chat from "./screens/Chat.jsx";
import DevLogin from "./screens/DevLogin.jsx";
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

function Main({ dev, onLogout }) {
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

export default function App() {
  const [dev, setDev] = useState(() => (inTelegram ? null : devUser.get()));

  return (
    <ToastProvider>
      {!inTelegram && !dev ? (
        <DevLogin onPick={(u) => { devUser.set(u); setDev(u); }} />
      ) : (
        <Main key={dev?.telegram_id} dev={dev} onLogout={() => { devUser.clear(); setDev(null); }} />
      )}
    </ToastProvider>
  );
}
