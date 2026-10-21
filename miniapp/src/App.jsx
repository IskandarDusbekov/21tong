import { useState } from "react";
import { Flame, LogOut, Route, Sun, Target, Trophy, Wrench } from "lucide-react";
import { api, devUser, inTelegram } from "./api.js";
import { ToastProvider, useLoad } from "./ui.jsx";
import Bounties from "./screens/Bounties.jsx";
import DevLogin from "./screens/DevLogin.jsx";
import Feed from "./screens/Feed.jsx";
import Journey from "./screens/Journey.jsx";
import Rating from "./screens/Rating.jsx";
import Today from "./screens/Today.jsx";

const TABS = [
  { id: "today", label: "Bugun", icon: Sun },
  { id: "journey", label: "Yo'l", icon: Route },
  { id: "feed", label: "Lenta", icon: Flame },
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
        {tab === "journey" && <Journey me={me} error={error} />}
        {tab === "feed" && <Feed me={me} />}
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
