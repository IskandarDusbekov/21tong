// "Rota" — rota chati: raportlar (ovoz/video o'ynatiladi), ogohlantirish, bosqich va matn xabarlari.
// Telegram guruh o'rniga. Chatga yozish faqat oyna ochiq bo'lganda — qolgan vaqt faqat kuzatish.
import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2, Eye, Flame, Hourglass, Lock, Mic, Moon, Play, Send,
  ShieldCheck, Sparkles, Sunrise, Users, Video, XCircle,
} from "lucide-react";
import { api, proofMedia } from "../api.js";
import { Avatar, Empty, ErrorCard, Skeleton, useAction, useLoad } from "../ui.jsx";
import { stageIcon } from "./Journey.jsx";

const REPORT_STATUS = {
  accepted: { tone: "ok", icon: CheckCircle2, label: "Qabul qilindi" },
  late: { tone: "bad", icon: XCircle, label: "Kech — qabul qilinmadi" },
  pending: { tone: "sun", icon: Hourglass, label: "Rota tekshirmoqda" },
  peer_approved: { tone: "ok", icon: CheckCircle2, label: "Rota tasdiqladi" },
  peer_rejected: { tone: "bad", icon: XCircle, label: "Rota rad etdi" },
};

const fmtTime = (iso) => {
  try {
    return new Date(iso).toLocaleTimeString("uz", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

/** Raport media'si: bosilganda Telegram'dan blob yuklab, o'ynaydi. */
function PlayButton({ media }) {
  const [state, setState] = useState("idle"); // idle | loading | ready | error
  const [url, setUrl] = useState(null);
  const ref = useRef(null);

  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);

  const load = async () => {
    setState("loading");
    try {
      const u = await proofMedia(media.kind, media.id);
      setUrl(u);
      setState("ready");
    } catch {
      setState("error");
    }
  };

  if (state === "error") return <span className="tag bad" style={{ marginTop: 8 }}>Media yuklanmadi</span>;
  if (state !== "ready") {
    return (
      <button className="play-btn" onClick={load} disabled={state === "loading"}>
        {state === "loading" ? <Hourglass size={16} /> : <Play size={16} fill="currentColor" />}
        {media.kind === "video" ? "Videoni ko'rish" : "Ovozni eshitish"}
      </button>
    );
  }
  return media.kind === "video" ? (
    <video className="chat-media" src={url} controls playsInline />
  ) : (
    <audio className="chat-audio" src={url} controls autoPlay />
  );
}

function ReportCard({ it }) {
  const s = REPORT_STATUS[it.status] || REPORT_STATUS.pending;
  const Kind = it.kind === "video" ? Video : Mic;
  return (
    <div className={`chat-report ${it.me ? "me" : ""} tone-${s.tone}`}>
      <div className="chat-report-head">
        <Avatar name={it.author} />
        <div className="chat-report-who">
          <b>{it.author}{it.me && <span className="tag" style={{ marginLeft: 6 }}>siz</span>}</b>
          <small className="muted"><Kind size={12} /> {it.kind === "video" ? "Video raport" : "Ovozli raport"} · {it.day_number}-kun</small>
        </div>
        <small className="muted num chat-time">{fmtTime(it.at)}</small>
      </div>
      {it.phrase && <div className="chat-phrase">«{it.phrase}»</div>}
      {it.media && <PlayButton media={it.media} />}
      <div className="chat-badges">
        <span className={`tag ${s.tone}`}><s.icon size={11} /> {s.label}</span>
        {it.admin_reviewed && <span className="tag info"><ShieldCheck size={11} /> Admin tekshirdi</span>}
      </div>
    </div>
  );
}

function SystemItem({ it }) {
  if (it.type === "strike") {
    return (
      <div className="chat-system bad">
        <XCircle size={15} />
        <span><b>{it.author}</b> — ogohlantirish ({it.reason})</span>
        <small className="muted num">{fmtTime(it.at)}</small>
      </div>
    );
  }
  const Icon = stageIcon({ icon: it.icon });
  return (
    <div className="chat-system ok">
      <Icon size={15} />
      <span><b>{it.author}</b> «{it.stage}» bosqichiga chiqdi · {it.day}-kun 🎖</span>
      <small className="muted num">{fmtTime(it.at)}</small>
    </div>
  );
}

function Bubble({ it }) {
  return (
    <div className={`chat-bubble ${it.me ? "me" : ""}`}>
      {!it.me && <Avatar name={it.author} size={30} />}
      <div className="chat-bubble-body">
        {!it.me && <b className="chat-bubble-author">{it.author}</b>}
        <p>{it.text}</p>
        <small className="chat-bubble-time num">{fmtTime(it.at)}</small>
      </div>
    </div>
  );
}

function ReflectionCard({ it, onFire }) {
  return (
    <div className="chat-reflection">
      <div className="chat-reflection-head">
        <Moon size={14} />
        <b>{it.author}{it.me && <span className="tag" style={{ marginLeft: 6 }}>siz</span>}</b>
        <small className="muted num chat-time">{fmtTime(it.at)}</small>
      </div>
      <p>{it.text}</p>
      <button
        className={`fire-btn ${it.fired_by_me ? "on" : ""}`} disabled={it.me || it.fired_by_me}
        onClick={() => onFire(it.id)} aria-label="Olov berish"
      >
        <Flame size={15} fill={it.fired_by_me ? "currentColor" : "none"} />
        <span className="num">{it.fires}</span>
      </button>
    </div>
  );
}

function ChatItem({ it, onFire }) {
  if (it.type === "report") return <ReportCard it={it} />;
  if (it.type === "message") return <Bubble it={it} />;
  if (it.type === "reflection") return <ReflectionCard it={it} onFire={onFire} />;
  return <SystemItem it={it} />;
}

function ReflectionPrompt({ max, onSent }) {
  const [text, setText] = useState("");
  const [run, busy] = useAction(() => { setText(""); onSent(); });
  return (
    <div className="card reflection-prompt">
      <div className="reflection-prompt-head"><Moon size={16} /> <b>Bugungi kun qanday o'tdi?</b></div>
      <textarea
        maxLength={max} value={text} onChange={(e) => setText(e.target.value)}
        placeholder="Bir-ikki gap bilan yozing — rotangiz ko'radi va 🔥 beradi."
      />
      <div className="row-between">
        <small className="num muted">{max - text.length}</small>
        <button className="btn btn-primary btn-sm" disabled={!text.trim() || busy} onClick={() => run(() => api.reflect(text), "Refleksiya qo'shildi")}>
          <Send size={15} /> Yuborish
        </button>
      </div>
    </div>
  );
}

function WindowBar({ w, roll }) {
  const prestart = w.which === "prestart";
  const Icon = prestart ? Users : w.which === "evening" ? Moon : Sunrise;
  return (
    <div className={`chat-window ${w.open ? "open" : "closed"}`}>
      <div className="chat-window-main">
        {w.open ? <Icon size={16} /> : <Lock size={16} />}
        <div>
          <b>{prestart ? "Tanishuv chati ochiq" : w.open ? `${w.label} ochiq` : "Chat yopiq"}</b>
          <small className="muted">
            {prestart ? "Start'gacha bemalol suhbatlashing"
              : w.open ? `${w.closes_at} gacha yozish mumkin`
              : <><Eye size={11} /> Faqat kuzatish · {w.label} {w.next_open} da ochiladi</>}
          </small>
        </div>
      </div>
      <span className="chat-roll" title="Rotada"><Users size={13} /> {prestart ? roll.total : `${roll.done}/${roll.total}`}</span>
    </div>
  );
}

function Composer({ open, nextOpen, onSent }) {
  const [text, setText] = useState("");
  const [run, busy] = useAction(() => { setText(""); onSent(); });
  if (!open) {
    return (
      <div className="chat-composer locked">
        <Lock size={16} />
        <span className="small">Oyna yopiq — faqat kuzatish. Chat <b className="num">{nextOpen}</b> da ochiladi.</span>
      </div>
    );
  }
  return (
    <div className="chat-composer">
      <input
        value={text} maxLength={1000} placeholder="Rotaga yozing — saf torting!"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && text.trim() && run(() => api.sendMessage(text))}
      />
      <button className="btn btn-primary chat-send" disabled={!text.trim() || busy} onClick={() => run(() => api.sendMessage(text))}>
        <Send size={18} />
      </button>
    </div>
  );
}

export default function Chat({ me }) {
  const { data, error, reload } = useLoad(api.chat);
  const [run] = useAction(reload);
  const listRef = useRef(null);

  // Oyna ochiq bo'lsa, yangi xabarlar uchun har 15 soniyada yangilab turamiz
  useEffect(() => {
    const id = setInterval(reload, 15000);
    return () => clearInterval(id);
  }, [reload]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [data?.items?.length]);

  if (!me?.membership && !me?.upcoming) {
    return <Empty icon={Users} title="Rota chati tasdiqlangach ochiladi" text="Arizangiz qabul qilingach, rotangiz shu yerda bo'ladi." />;
  }
  if (error && !data) return <ErrorCard text={error} />;
  if (!data) return <div className="stack"><Skeleton height={64} /><Skeleton height={300} /></div>;

  return (
    <div className="chat">
      <div className="screen-head" style={{ marginBottom: 10 }}>
        <div>
          <h2>{data.squad}</h2>
          <p className="muted small">{data.tribe}{data.prestart ? " · Start oldidan" : ` · ${data.day_number}-kun`}</p>
        </div>
        <div className="window-icon" style={{ background: "var(--sun-soft)", color: "var(--sun)" }}><Flame size={18} /></div>
      </div>

      <WindowBar w={data.window} roll={data.roll} />

      <div className="chat-list" ref={listRef}>
        {data.items.length === 0 ? (
          <Empty
            icon={Sparkles} title="Hali tinch"
            text={data.prestart ? "Rotadoshlaringiz bilan tanishing — birinchi xabarni yozing." : "Birinchi raport va xabarlar shu yerda paydo bo'ladi."}
          />
        ) : (
          data.items.map((it, i) => <ChatItem key={`${it.type}-${it.at}-${i}`} it={it} onFire={(id) => run(() => api.fire(id))} />)
        )}
      </div>

      {data.can_reflect && <ReflectionPrompt max={me.reflection_max_length || 200} onSent={reload} />}
      <Composer open={data.window.open} nextOpen={data.window.next_open} onSent={reload} />
    </div>
  );
}
