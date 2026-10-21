import { useCallback, useEffect, useState } from "react";
import { api, tg } from "./api.js";

const TABS = [
  { id: "today", label: "Bugun", icon: "☀️" },
  { id: "feed", label: "Lenta", icon: "🔥" },
  { id: "bounty", label: "Bounty", icon: "🎯" },
  { id: "rating", label: "Reyting", icon: "🏆" },
];

function haptic(type = "success") {
  tg?.HapticFeedback?.notificationOccurred(type);
}

function useLoad(fn) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const reload = useCallback(() => {
    fn().then(setData).catch((e) => setError(e.message));
  }, [fn]);
  useEffect(reload, [reload]);
  return { data, error, reload, setError };
}

export default function App() {
  const [tab, setTab] = useState("today");
  return (
    <div className="app">
      <main>
        {tab === "today" && <Today />}
        {tab === "feed" && <Feed />}
        {tab === "bounty" && <Bounties />}
        {tab === "rating" && <Rating />}
      </main>
      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
            <span>{t.icon}</span>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}

function Step({ done, label, hint }) {
  return (
    <li className={done ? "step done" : "step"}>
      <span className="check">{done ? "✓" : ""}</span>
      <div>
        <div>{label}</div>
        {hint && <small>{hint}</small>}
      </div>
    </li>
  );
}

function Today() {
  const { data: me, error, reload, setError } = useLoad(api.me);
  const [busy, setBusy] = useState(false);

  const act = async (fn, okMsg) => {
    setBusy(true);
    try {
      await fn();
      haptic();
      if (okMsg) tg?.showAlert?.(okMsg);
      reload();
    } catch (e) {
      haptic("error");
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (error && !me) return <p className="error">{error}</p>;
  if (!me) return <p className="muted">Yuklanmoqda…</p>;

  const m = me.membership;
  const t = me.today;
  const videoLabel = { reviewing: "tekshirilmoqda", approved: "tasdiqlandi", rejected: "rad etildi" };

  return (
    <section>
      <header className="hero">
        <div className="muted">{m ? m.tribe : "Faol oqim yo'q"}</div>
        <h1>{t ? `${t.day_number}-kun` : "21 Tong"}</h1>
        {t && <div className="alarm">⏰ {t.alarm_time}</div>}
        {me.stage && <div className="badge">🏅 {me.stage.name}</div>}
      </header>

      <div className="stats">
        <div><b>{m ? `${m.strikes}/${me.max_strikes}` : "–"}</b><small>Strike</small></div>
        <div><b>{me.jokers}</b><small>Joker 🃏</small></div>
        <div><b>{me.coins}</b><small>IrodaCoin</small></div>
      </div>

      {error && <p className="error">{error}</p>}

      {t && t.status === "pending" && (
        <>
          <ul className="steps">
            <Step done={t.woke} label="«Uyg'ondim» tugmasi" />
            <Step done={t.voice} label="Guruhga ovozli xabar" hint="Botdagi gapni ovoz chiqarib o'qing" />
            {t.video_required && (
              <Step
                done={t.video === "approved"}
                label="10 soniyalik video krujok"
                hint={t.video ? `Video ${videoLabel[t.video]}` : "Tashqariga chiqing, suv iching, botga yuboring"}
              />
            )}
          </ul>
          {!t.woke && (
            <button className="primary big" disabled={busy} onClick={() => act(api.wake)}>
              ☀️ Uyg'ondim
            </button>
          )}
        </>
      )}
      {t && t.status === "frozen" && <p className="card">❄️ Bugun muzlatilgan kun. Tezroq tuzaling!</p>}
      {t && t.status === "completed" && <p className="card">✅ Bugungi kun bajarildi. Zo'r!</p>}

      {m && !m.freeze_used && (
        <button
          className="ghost"
          disabled={busy}
          onClick={() =>
            tg?.showConfirm
              ? tg.showConfirm("Ertangi kunni muzlatasizmi? Bu butun oqimda faqat 1 marta.", (ok) =>
                  ok && act(() => api.freeze(""), "Ertangi kun muzlatildi."))
              : act(() => api.freeze(""), "Ertangi kun muzlatildi.")
          }
        >
          ❄️ Ertangi kunni muzlatish (kasallik)
        </button>
      )}
    </section>
  );
}

function Feed() {
  const { data, error, reload, setError } = useLoad(api.feed);
  const [text, setText] = useState("");
  const mine = data?.some((r) => r.mine);

  const send = async () => {
    try {
      await api.reflect(text);
      setText("");
      haptic();
      reload();
    } catch (e) {
      setError(e.message);
    }
  };
  const fire = async (id) => {
    try {
      await api.fire(id);
      haptic();
      reload();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <section>
      <h2>Bugungi kun qanday o'tdi?</h2>
      {error && <p className="error">{error}</p>}
      {!mine && (
        <div className="card">
          <textarea maxLength={200} value={text} onChange={(e) => setText(e.target.value)} placeholder="Qisqa refleksiya…" />
          <div className="row">
            <small className="muted">{text.length}/200</small>
            <button className="primary" disabled={!text.trim()} onClick={send}>Yuborish</button>
          </div>
        </div>
      )}
      {data?.length === 0 && <p className="muted">Hali hech kim yozmadi. Birinchi bo'ling!</p>}
      {data?.map((r) => (
        <div key={r.id} className="card post">
          <b>{r.author}</b>
          <p>{r.text}</p>
          <button className={r.fired_by_me ? "fire on" : "fire"} disabled={r.mine || r.fired_by_me} onClick={() => fire(r.id)}>
            🔥 {r.fires}
          </button>
        </div>
      ))}
    </section>
  );
}

function Bounties() {
  const { data, error, reload, setError } = useLoad(api.bounties);
  const complete = async (id) => {
    try {
      await api.completeBounty(id);
      haptic();
      reload();
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <section>
      <h2>Kunduzgi topshiriqlar</h2>
      {error && <p className="error">{error}</p>}
      {data?.length === 0 && <p className="muted">Bugun topshiriq yo'q.</p>}
      {data?.map((b) => (
        <div key={b.id} className="card">
          <div className="row">
            <b>{b.title}</b>
            <span className="badge">+{b.reward}</span>
          </div>
          {b.description && <p className="muted">{b.description}</p>}
          <button className="primary" disabled={b.done} onClick={() => complete(b.id)}>
            {b.done ? "Bajarildi ✓" : "Bajardim"}
          </button>
        </div>
      ))}
    </section>
  );
}

function Rating() {
  const { data, error } = useLoad(api.leaderboard);
  return (
    <section>
      <h2>IrodaCoin reytingi</h2>
      {error && <p className="error">{error}</p>}
      <ol className="rating">
        {data?.map((r, i) => (
          <li key={i} className={r.me ? "me" : ""}>
            <span>{i + 1}. {r.name}</span>
            <b>{r.coins}</b>
          </li>
        ))}
      </ol>
    </section>
  );
}
