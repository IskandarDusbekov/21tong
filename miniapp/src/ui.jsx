// Umumiy UI bo'laklari: ma'lumot yuklash, toast, tasdiqlash oynasi, avatar, bo'sh holat.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, Moon, Smartphone, Sun, Volume2, VolumeX } from "lucide-react";
import { tg } from "./api.js";
import { sound } from "./sound.js";
import { getTheme, setTheme } from "./theme.js";

export function haptic(type = "success") {
  tg?.HapticFeedback?.notificationOccurred(type);
}

const THEMES = [
  { id: "", label: "Avto", icon: Smartphone },
  { id: "light", label: "Yorug'", icon: Sun },
  { id: "dark", label: "Tungi", icon: Moon },
];

/** Light/night rejimi — Profil → Sozlamalar. "Avto" Telegram mavzusiga ergashadi. */
export function ThemeSwitch() {
  const [theme, set] = useState(getTheme);
  return (
    <div className="seg seg-accent" role="radiogroup" aria-label="Rejim" style={{ marginBottom: 0 }}>
      {THEMES.map(({ id, label, icon: Icon }) => (
        <button
          key={id || "auto"} role="radio" aria-checked={theme === id} className={theme === id ? "on" : ""}
          onClick={() => { setTheme(id); set(id); haptic("success"); }}
        >
          <Icon size={14} /> {label}
        </button>
      ))}
    </div>
  );
}

/** Ovoz belgilari — Profil → Sozlamalar. */
export function SoundSwitch() {
  const [muted, setMuted] = useState(sound.muted);
  return (
    <button className={`switch ${muted ? "" : "on"}`} role="switch" aria-checked={!muted} onClick={() => setMuted(sound.toggle())}>
      {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
      <i />
    </button>
  );
}

export function useLoad(fn) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const reload = useCallback(() => {
    fn().then((d) => { setData(d); setError(""); }).catch((e) => setError(e.message));
  }, [fn]);
  useEffect(reload, [reload]);
  return { data, error, reload };
}

const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const timer = useRef();
  const show = useCallback((text, kind = "ok") => {
    haptic(kind === "error" ? "error" : "success");
    setToast({ text, kind, id: Date.now() });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(null), 2800);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <div key={toast.id} className={`toast ${toast.kind}`} role="status">
          {toast.kind === "error" ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          {toast.text}
        </div>
      )}
    </ToastContext.Provider>
  );
}

/** Amal bajaradi, natijani toast bilan ko'rsatadi. */
export function useAction(onDone) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const run = async (fn, okText) => {
    setBusy(true);
    try {
      const result = await fn();
      if (okText) { toast(okText); sound.success(); }
      onDone?.(result);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  return [run, busy];
}

export function Sheet({ icon: Icon, tone = "var(--sun)", title, text, confirm, onConfirm, onClose }) {
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-icon" style={{ background: `color-mix(in srgb, ${tone} 15%, transparent)`, color: tone }}>
          <Icon size={26} />
        </div>
        <h3>{title}</h3>
        <p>{text}</p>
        <div className="sheet-actions">
          <button className="btn btn-soft" onClick={onClose}>Bekor qilish</button>
          <button className="btn btn-primary" onClick={() => { onConfirm(); onClose(); }}>{confirm}</button>
        </div>
      </div>
    </div>
  );
}

const AVATAR_COLORS = ["#ff7a2f", "#6c7bff", "#22b26b", "#e0559a", "#2eb3d9", "#a26bff", "#d99b1c"];

export function Avatar({ name = "?", size }) {
  const color = AVATAR_COLORS[[...name].reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_COLORS.length];
  return (
    <span className="avatar" style={{ background: color, ...(size && { width: size, height: size }) }}>
      {name.trim()[0]?.toUpperCase() || "?"}
    </span>
  );
}

export function Empty({ icon: Icon, title, text }) {
  return (
    <div className="empty">
      <div className="empty-icon"><Icon size={26} /></div>
      <b>{title}</b>
      {text && <p className="small">{text}</p>}
    </div>
  );
}

export function Skeleton({ height = 120 }) {
  return <div className="skeleton" style={{ height }} />;
}

export function ErrorCard({ text }) {
  return (
    <div className="banner bad">
      <div className="banner-icon"><AlertCircle size={22} /></div>
      <div>{text}</div>
    </div>
  );
}
