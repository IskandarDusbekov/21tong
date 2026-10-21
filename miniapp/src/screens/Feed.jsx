import { useState } from "react";
import { Flame, Lock, MessageCircleHeart, Moon, Send } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorCard, Skeleton, useAction, useLoad } from "../ui.jsx";

const MAX = 200;

function Composer({ evening, onSent }) {
  const [text, setText] = useState("");
  const [run, busy] = useAction(() => { setText(""); onSent(); });

  if (!evening.open) {
    return (
      <div className="card lock-note">
        <div className="window-icon"><Lock size={18} /></div>
        <div>
          <b style={{ color: "var(--text)" }}>Kechki oyna yopiq</b>
          <small style={{ display: "block" }} className="num">Refleksiya {evening.start}–{evening.end} da yoziladi</small>
        </div>
      </div>
    );
  }
  const left = MAX - text.length;
  return (
    <div className="card composer">
      <textarea
        maxLength={MAX} value={text} onChange={(e) => setText(e.target.value)}
        placeholder="Bugun nima o'zgardi? Qayerda qiyin bo'ldi?" aria-label="Refleksiya"
      />
      <div className="composer-foot">
        <small className="num" style={{ color: left < 20 ? "var(--bad)" : "var(--muted)" }}>{left}</small>
        <button className="btn btn-primary" disabled={!text.trim() || busy} onClick={() => run(() => api.reflect(text), "Refleksiya qo'shildi")}>
          <Send size={16} /> Yuborish
        </button>
      </div>
    </div>
  );
}

function Post({ r, onFire }) {
  return (
    <div className="card post">
      <Avatar name={r.author} />
      <div className="post-body">
        <b>{r.author}{r.mine && <span className="tag" style={{ marginLeft: 6 }}>siz</span>}</b>
        <p>{r.text}</p>
        <button
          className={`fire-btn ${r.fired_by_me ? "on" : ""}`} disabled={r.mine || r.fired_by_me}
          onClick={() => onFire(r.id)} aria-label="Olov berish"
        >
          <Flame size={16} fill={r.fired_by_me ? "currentColor" : "none"} />
          <span className="num">{r.fires}</span>
        </button>
      </div>
    </div>
  );
}

export default function Feed({ me }) {
  const { data, error, reload } = useLoad(api.feed);
  const [run] = useAction(reload);
  const evening = me?.journey?.windows.evening;
  const mine = data?.some((r) => r.mine);

  return (
    <div>
      <div className="screen-head">
        <div>
          <h2>Bugungi kun qanday o'tdi?</h2>
          <p className="muted small">Faqat o'z qabilangiz ko'radi · maks {MAX} belgi</p>
        </div>
        <div className="window-icon" style={{ background: "var(--rest-soft)", color: "var(--rest)" }}><Moon size={18} /></div>
      </div>

      {error && !data && <ErrorCard text={error} />}
      {evening && !mine && data && <div style={{ marginBottom: 14 }}><Composer evening={evening} onSent={reload} /></div>}

      {!data && !error && <div className="stack"><Skeleton height={96} /><Skeleton height={96} /></div>}
      {data?.length === 0 && <Empty icon={MessageCircleHeart} title="Hali hech kim yozmadi" text="Birinchi bo'lib bugungi kuningiz haqida yozing." />}
      <div className="stack">
        {data?.map((r) => <Post key={r.id} r={r} onFire={(id) => run(() => api.fire(id))} />)}
      </div>
    </div>
  );
}
