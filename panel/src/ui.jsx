// Panelning umumiy komponentlari va yordamchilari.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, Minus, Plus, X } from "lucide-react";

// --- Ma'lumot yuklash -----------------------------------------------------------

export function useLoad(fn, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(fn, deps);
  const reload = useCallback(() => {
    setLoading(true);
    return load()
      .then((d) => { setData(d); setError(""); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [load]);
  useEffect(() => { reload(); }, [reload]);
  return { data, setData, error, loading, reload };
}

// --- Toast ----------------------------------------------------------------------

const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const show = useCallback((text, kind = "ok") => {
    const id = Math.random();
    setItems((xs) => [...xs, { id, text, kind }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      <div className="toast-host" role="status">
        {items.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            {t.kind === "error" ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

/** Amalni bajaradi va natijani toast bilan ko'rsatadi. */
export function useAction(onDone) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const run = async (fn, okText) => {
    setBusy(true);
    try {
      const r = await fn();
      const text = typeof okText === "function" ? okText(r) : okText || r?.detail;
      if (text) toast(text);
      await onDone?.(r);
      return r;
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  return [run, busy];
}

// --- Tasdiqlash oynasi --------------------------------------------------------------

const ConfirmCtx = createContext(() => Promise.resolve(false));
export const useConfirm = () => useContext(ConfirmCtx);

export function ConfirmProvider({ children }) {
  const [state, setState] = useState(null);
  const resolver = useRef();
  const confirm = useCallback((opts) => new Promise((resolve) => {
    resolver.current = resolve;
    setState(opts);
  }), []);
  const close = (v) => { resolver.current?.(v); setState(null); };
  return (
    <ConfirmCtx.Provider value={confirm}>
      {children}
      {state && (
        <>
          <div className="backdrop modal-backdrop" onClick={() => close(false)} />
          <div className="card modal" role="dialog" aria-modal="true">
            <h2>{state.title}</h2>
            <p>{state.text}</p>
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-ghost" onClick={() => close(false)}>Bekor qilish</button>
              <button className={`btn ${state.danger ? "btn-bad" : "btn-primary"}`} onClick={() => close(true)} autoFocus>
                {state.confirm || "Tasdiqlash"}
              </button>
            </div>
          </div>
        </>
      )}
    </ConfirmCtx.Provider>
  );
}

// --- Kichik komponentlar -------------------------------------------------------------

const AVATAR_COLORS = ["#f26b21", "#4e5fe0", "#1a9e5f", "#d14d8f", "#1b9cc4", "#8a5cf0", "#c98100"];

export function Avatar({ name = "?", size }) {
  const color = AVATAR_COLORS[[...name].reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_COLORS.length];
  return (
    <span className="avatar" style={{ background: color, ...(size && { width: size, height: size, fontSize: size * 0.4 }) }}>
      {name.trim()[0]?.toUpperCase() || "?"}
    </span>
  );
}

export function Person({ user, sub }) {
  return (
    <div className="person">
      <Avatar name={user.name} />
      <div style={{ minWidth: 0 }}>
        <b>{user.name}</b>
        <small>{sub ?? (user.username ? `@${user.username}` : user.telegram_id)}</small>
      </div>
    </div>
  );
}

export const GENDER = { M: "Yigit", F: "Qiz" };

export const TODAY_STATUS = {
  done: { label: "Raport berdi", tone: "ok" },
  woke: { label: "Turdi, raport yo'q", tone: "warn" },
  absent: { label: "Javob yo'q", tone: "bad" },
  frozen: { label: "Muzlatilgan", tone: "ice" },
  rest: { label: "Yakshanba", tone: "info" },
  out: { label: "Chiqarilgan", tone: "mute" },
};

export const MEMBER_STATUS = {
  active: { label: "Faol", tone: "ok" },
  expelled: { label: "Chiqarilgan", tone: "bad" },
  finished: { label: "Tugatgan", tone: "info" },
  mentor: { label: "Mentor", tone: "sun" },
};

export function Pill({ tone = "mute", children, dot }) {
  return <span className={`pill tone-${tone}`}>{dot && <i className="dot" />}{children}</span>;
}

export function StatusPill({ map, value }) {
  const s = map[value] || { label: value, tone: "mute" };
  return <Pill tone={s.tone} dot>{s.label}</Pill>;
}

export function StrikeDots({ count, max }) {
  return (
    <span className="strike-dots" title={`${count}/${max} ogohlantirish`}>
      {Array.from({ length: max }, (_, i) => <i key={i} className={i < count ? "on" : ""} />)}
    </span>
  );
}

export function Empty({ icon: Icon, title, text, children }) {
  return (
    <div className="empty">
      <div className="empty-icon"><Icon size={24} /></div>
      <b>{title}</b>
      {text && <div className="small">{text}</div>}
      {children && <div style={{ marginTop: 14 }}>{children}</div>}
    </div>
  );
}

export function Skeleton({ height = 120, style }) {
  return <div className="skeleton" style={{ height, ...style }} />;
}

export function ErrorBox({ text }) {
  return <div className="alert tone-bad"><AlertCircle size={18} /> {text}</div>;
}

export function Switch({ on, onChange, label }) {
  return <button type="button" role="switch" aria-checked={on} aria-label={label} className={`switch ${on ? "on" : ""}`} onClick={() => onChange(!on)} />;
}

export function Stepper({ value, onChange, min = 0, max = 999 }) {
  const set = (v) => onChange(Math.min(max, Math.max(min, Number.isNaN(v) ? min : v)));
  return (
    <div className="stepper">
      <button type="button" onClick={() => set(value - 1)} aria-label="Kamaytirish"><Minus size={15} /></button>
      <input value={value} onChange={(e) => set(parseInt(e.target.value, 10))} inputMode="numeric" />
      <button type="button" onClick={() => set(value + 1)} aria-label="Oshirish"><Plus size={15} /></button>
    </div>
  );
}

export function Seg({ value, onChange, options }) {
  return (
    <div className="seg" role="tablist">
      {options.map((o) => (
        <button key={o.value} className={value === o.value ? "on" : ""} onClick={() => onChange(o.value)} role="tab" aria-selected={value === o.value}>
          {o.label}{o.count != null && <span className="n">{o.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Drawer({ onClose, title, children, actions }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <>
      <div className="backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true">
        <div className="drawer-head">
          <div style={{ flex: 1, minWidth: 0 }}>{title}</div>
          {actions}
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Yopish"><X size={18} /></button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}

export function PageHead({ title, sub, children }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {sub && <p>{sub}</p>}
      </div>
      {children && <div className="page-actions">{children}</div>}
    </div>
  );
}

// --- Telegram xabari ko'rinishi --------------------------------------------------------

const ALLOWED_TAGS = /&lt;(\/?)(b|i|u|s|code|blockquote)&gt;/g;

/** Telegram HTML'ini xavfsiz ko'rsatish: avval hammasi escape, keyin faqat ruxsat etilgan teglar tiklanadi. */
export function TgBubble({ html }) {
  const safe = String(html)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(ALLOWED_TAGS, "<$1$2>");
  return <div className="tg-bubble" dangerouslySetInnerHTML={{ __html: safe }} />;
}

// --- Formatlash ---------------------------------------------------------------------

const MONTHS = ["yan", "fev", "mar", "apr", "may", "iyun", "iyul", "avg", "sen", "okt", "noy", "dek"];

export function fmtDate(v) {
  if (!v) return "—";
  const d = new Date(v);
  return `${d.getDate()}-${MONTHS[d.getMonth()]}`;
}

export function fmtAgo(v) {
  const s = (Date.now() - new Date(v).getTime()) / 1000;
  if (s < 60) return "hozirgina";
  if (s < 3600) return `${Math.floor(s / 60)} daqiqa oldin`;
  if (s < 86400) return `${Math.floor(s / 3600)} soat oldin`;
  return `${Math.floor(s / 86400)} kun oldin`;
}
