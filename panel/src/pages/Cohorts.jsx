import { useState } from "react";
import { CalendarPlus, CalendarRange, CopyPlus, DoorOpen, Flag, Pencil, Play, Plus, RefreshCw, Timer, Trash2 } from "lucide-react";
import { api } from "../api.js";
import { Drawer, Empty, ErrorBox, PageHead, Pill, Skeleton, Switch, fmtDate, useAction, useConfirm, useLoad } from "../ui.jsx";

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

/** Tayyor rota vaqtlari — foydalanuvchi arizada shulardan birini tanlaydi. */
function Slots({ cohort, onChanged }) {
  const confirm = useConfirm();
  const [form, setForm] = useState({ start_wake_time: "06:00", target_wake_time: "05:00", title: "" });
  const [run, busy] = useAction(onChanged);
  const add = (e) => {
    e.preventDefault();
    run(() => api.addSlot(cohort.id, form), "Rota vaqti qo'shildi.");
  };
  const remove = async (s) => {
    if (await confirm({ title: "Rota vaqtini o'chirasizmi?", text: `${s.start_wake_time} → ${s.target_wake_time}. Allaqachon joylashganlar o'z rotasida qoladi.`, confirm: "O'chirish", danger: true })) {
      run(() => api.deleteSlot(s.id), "O'chirildi.");
    }
  };
  return (
    <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--line)" }}>
      <div className="row-between" style={{ marginBottom: 8 }}>
        <div><h3>Tayyor rotalar</h3><div className="muted small">Arizada foydalanuvchi shulardan birini tanlaydi — budilnigi shunga moslashadi.</div></div>
      </div>
      {cohort.slots.length === 0 && (
        <div className="alert tone-warn" style={{ marginBottom: 10 }}>Rota vaqti yo'q — foydalanuvchilar ariza oxirida tanlay olmaydi. 3–4 ta qo'shing.</div>
      )}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: 10 }}>
        {cohort.slots.map((s) => (
          <div key={s.id} className="card card-pad" style={{ padding: "12px 14px", opacity: s.is_open ? 1 : 0.55, boxShadow: "none" }}>
            <div className="row-between">
              <b className="num" style={{ fontSize: 18 }}>{s.start_wake_time} <span style={{ color: "var(--sun)" }}>→</span> {s.target_wake_time}</b>
              <button className="btn btn-ghost btn-icon" onClick={() => remove(s)} aria-label="O'chirish"><Trash2 size={15} /></button>
            </div>
            {s.title && <div className="small" style={{ fontWeight: 600 }}>{s.title}</div>}
            <div className="row-between small muted" style={{ marginTop: 6 }}>
              <span>{s.members} joylashgan · {s.pending} ariza</span>
              <span className="row" style={{ gap: 6 }}>{s.is_open ? "ochiq" : "yopiq"}
                <Switch on={s.is_open} onChange={(v) => run(() => api.updateSlot(s.id, { is_open: v }))} label="Tanlash mumkin" />
              </span>
            </div>
          </div>
        ))}
      </div>
      <form className="row" style={{ flexWrap: "wrap", gap: 8, marginTop: 10 }} onSubmit={add}>
        <input type="time" className="input" style={{ width: 120 }} value={form.start_wake_time} onChange={(e) => setForm({ ...form, start_wake_time: e.target.value })} aria-label="Boshlang'ich vaqt" />
        <span className="muted">→</span>
        <input type="time" className="input" style={{ width: 120 }} value={form.target_wake_time} onChange={(e) => setForm({ ...form, target_wake_time: e.target.value })} aria-label="Maqsad vaqti" />
        <input className="input" style={{ flex: "1 1 160px" }} placeholder="Nomi (ixtiyoriy), masalan «Erta qushlar»" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <button className="btn btn-outline" disabled={busy}><Plus size={15} /> Rota qo'shish</button>
      </form>
    </div>
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
                {c.status === "recruiting" && (
                  <div style={{ marginTop: 8 }}>
                    <Pill tone="sun"><Timer size={12} /> {c.days_left > 0 ? `Startga ${c.days_left} kun qoldi` : "Bugun start"}</Pill>
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
                <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => action(c, "clone_next", {
                  title: "Keyingi oqimni ochasizmi?",
                  text: `Start ${fmtDate(c.start_date)} dan 7 kun keyin. Shu oqimning chat oynalari va rota vaqtlari ko'chiriladi.`,
                  confirm: "Ochish",
                })}><CopyPlus size={14} /> Keyingi oqim (+7 kun)</button>
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
            {c.status !== "finished" && <Slots cohort={c} onChanged={reload} />}
          </div>
        ))}
      </div>
      {editing && <CohortForm initial={editing} onSave={save} onClose={() => setEditing(null)} busy={busy} />}
    </>
  );
}
