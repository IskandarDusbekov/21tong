import { useState } from "react";
import { CalendarPlus, CalendarRange, DoorOpen, Flag, Pencil, Play, RefreshCw } from "lucide-react";
import { api } from "../api.js";
import { Drawer, Empty, ErrorBox, PageHead, Pill, Skeleton, fmtDate, useAction, useConfirm, useLoad } from "../ui.jsx";

const STATUS_TONE = { recruiting: "sun", running: "ok", finished: "mute" };
const hm = (t) => (t || "").slice(0, 5);

function CohortForm({ initial, onSave, onClose, busy }) {
  const [f, setF] = useState(() => ({
    ...initial,
    morning_window_start: hm(initial.morning_window_start), morning_window_end: hm(initial.morning_window_end),
    evening_window_start: hm(initial.evening_window_start), evening_window_end: hm(initial.evening_window_end),
  }));
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <Drawer onClose={onClose} title={<h2>{initial.id ? "Oqimni tahrirlash" : "Yangi oqim"}</h2>}>
      <form className="stack" onSubmit={(e) => { e.preventDefault(); onSave(f); }}>
        <div className="field"><label>Nomi</label><input className="input" value={f.name || ""} onChange={set("name")} placeholder="Masalan: 2-oqim (Noyabr)" required /></div>
        <div className="grid grid-2">
          <div className="field"><label>Boshlanish sanasi</label><input type="date" className="input" value={f.start_date || ""} onChange={set("start_date")} required /></div>
          <div className="field"><label>Davomiyligi (kun)</label><input type="number" min="1" max="365" className="input" value={f.duration_days} onChange={set("duration_days")} /></div>
        </div>
        <div className="card card-pad">
          <h3 style={{ marginBottom: 4 }}>Chat oynalari</h3>
          <p className="muted small" style={{ marginTop: 0 }}>Rota guruhlari faqat shu vaqtlarda ochiq bo'ladi.</p>
          <div className="grid grid-2">
            <div className="field"><label>Tonggi oyna</label>
              <div className="row"><input type="time" className="input" value={f.morning_window_start} onChange={set("morning_window_start")} />—<input type="time" className="input" value={f.morning_window_end} onChange={set("morning_window_end")} /></div>
            </div>
            <div className="field"><label>Kechki oyna</label>
              <div className="row"><input type="time" className="input" value={f.evening_window_start} onChange={set("evening_window_start")} />—<input type="time" className="input" value={f.evening_window_end} onChange={set("evening_window_end")} /></div>
            </div>
          </div>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Bekor qilish</button>
          <button className="btn btn-primary" disabled={busy}>{initial.id ? "Saqlash" : "Oqim yaratish"}</button>
        </div>
      </form>
    </Drawer>
  );
}

export default function Cohorts() {
  const confirm = useConfirm();
  const { data, error, reload } = useLoad(api.cohorts);
  const [editing, setEditing] = useState(null);
  const [run, busy] = useAction(reload);

  const action = async (c, act, ask) => {
    if (ask && !(await confirm(ask))) return;
    run(() => api.cohortAction(c.id, act));
  };
  const save = (f) => run(
    () => (f.id ? api.updateCohort(f.id, f) : api.createCohort(f)),
    f.id ? "Oqim saqlandi." : "Oqim yaratildi. Endi «Qabulni ochish» tugmasini bosing.",
  ).then((r) => r && setEditing(null));

  return (
    <>
      <PageHead title="Oqimlar" sub="Har bir oqim — 21 kunlik lager. Qabul ochiq oqimga yangi qabul qilinganlar avtomatik tushadi.">
        <button className="btn btn-outline" disabled={busy || !data?.items.length} onClick={() => action(data.items[0], "run_daily", {
          title: "Kunlik hisobni hozir ishga tushirasizmi?",
          text: "Kechagi barcha kunlar baholanadi (ogohlantirishlar beriladi) va bugungi kunlar ochiladi. Odatda bu har kecha avtomatik bajariladi.",
          confirm: "Ishga tushirish",
        })}><RefreshCw size={16} /> Kunlik hisob</button>
        <button className="btn btn-primary" onClick={() => setEditing({ ...data?.defaults })}><CalendarPlus size={16} /> Yangi oqim</button>
      </PageHead>
      {error && <ErrorBox text={error} />}
      {!data && !error && <Skeleton height={200} />}
      {data && !data.items.length && (
        <div className="card"><Empty icon={CalendarRange} title="Hali oqim yo'q" text="Birinchi oqimni yarating.">
          <button className="btn btn-primary" onClick={() => setEditing({ ...data.defaults })}><CalendarPlus size={16} /> Yangi oqim</button>
        </Empty></div>
      )}
      <div className="stack">
        {data?.items.map((c) => (
          <div key={c.id} className="card card-pad">
            <div className="row" style={{ flexWrap: "wrap", gap: 16 }}>
              <div style={{ flex: "1 1 260px", minWidth: 0 }}>
                <div className="row" style={{ gap: 10, marginBottom: 4 }}>
                  <h2>{c.name}</h2>
                  <Pill tone={STATUS_TONE[c.status]} dot>{c.status_label}</Pill>
                </div>
                <div className="muted small">
                  {fmtDate(c.start_date)} — {fmtDate(c.end_date)} · {c.duration_days} kun · tong {hm(c.morning_window_start)}–{hm(c.morning_window_end)}, kech {hm(c.evening_window_start)}–{hm(c.evening_window_end)}
                </div>
                {c.status === "running" && c.day && (
                  <div className="row" style={{ marginTop: 10, gap: 10 }}>
                    <div className="progress" style={{ flex: 1 }}><i style={{ width: `${(c.day / c.duration_days) * 100}%` }} /></div>
                    <span className="small num"><b>{c.day}</b>/{c.duration_days}-kun</span>
                  </div>
                )}
              </div>
              <div className="row" style={{ gap: 18 }}>
                <div><b className="num" style={{ fontSize: 18 }}>{c.active}</b><div className="muted small">faol</div></div>
                <div><b className="num" style={{ fontSize: 18 }}>{c.expelled}</b><div className="muted small">chiqarilgan</div></div>
                <div><b className="num" style={{ fontSize: 18 }}>{c.squads}</b><div className="muted small">rota</div></div>
              </div>
              <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
                <button className="btn btn-ghost btn-sm" onClick={() => setEditing(c)}><Pencil size={14} /> Tahrirlash</button>
                {c.status !== "recruiting" && (
                  <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => action(c, "open")}><DoorOpen size={14} /> Qabulni ochish</button>
                )}
                {c.status !== "running" && (
                  <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => action(c, "start", {
                    title: `«${c.name}» ni hozir boshlaysizmi?`, text: "Odatda oqim boshlanish sanasida avtomatik boshlanadi.", confirm: "Boshlash",
                  })}><Play size={14} /> Boshlash</button>
                )}
                {c.status !== "finished" && (
                  <button className="btn btn-bad btn-sm" disabled={busy} onClick={() => action(c, "finish", {
                    title: `«${c.name}» ni yakunlaysizmi?`, text: "Barcha faol ishtirokchilar «tugatgan» holatiga o'tadi.", confirm: "Yakunlash", danger: true,
                  })}><Flag size={14} /> Yakunlash</button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
      {editing && <CohortForm initial={editing} onSave={save} onClose={() => setEditing(null)} busy={busy} />}
    </>
  );
}
