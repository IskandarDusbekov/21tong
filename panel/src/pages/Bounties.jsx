import { useState } from "react";
import { Coins, Plus, Target, Trash2 } from "lucide-react";
import { api } from "../api.js";
import { Empty, ErrorBox, PageHead, Pill, Skeleton, fmtDate, useAction, useConfirm, useLoad } from "../ui.jsx";

export default function Bounties() {
  const confirm = useConfirm();
  const { data, error, reload } = useLoad(api.bounties);
  const [run, busy] = useAction(reload);
  const [f, setF] = useState(null);

  const open = () => setF({ cohort: data?.cohorts[0]?.id, date: data?.today, title: "", description: "", reward: 10 });
  const create = (e) => {
    e.preventDefault();
    run(() => api.createBounty(f), "Topshiriq qo'shildi.").then((r) => r && setF(null));
  };
  const remove = async (b) => {
    if (await confirm({ title: "Topshiriqni o'chirasizmi?", text: `«${b.title}». Bajarganlar tangasi saqlanadi.`, confirm: "O'chirish", danger: true }))
      run(() => api.deleteBounty(b.id), "O'chirildi.");
  };

  return (
    <>
      <PageHead title="Kunduzgi topshiriqlar" sub="«Bounty» — ixtiyoriy kunduzgi topshiriqlar (kitob o'qish, sport...). Bajarganlar IrodaCoin oladi.">
        <button className="btn btn-primary" disabled={!data?.cohorts.length} onClick={open}><Plus size={16} /> Yangi topshiriq</button>
      </PageHead>
      {error && <ErrorBox text={error} />}
      {!data && !error && <Skeleton height={200} />}
      {data && !data.cohorts.length && (
        <div className="card"><Empty icon={Target} title="Davom etayotgan oqim yo'q" text="Topshiriq yozish uchun avval oqim boshlang." /></div>
      )}
      {f && (
        <form className="card card-pad stack" onSubmit={create} style={{ marginBottom: 14 }}>
          <h3 style={{ marginTop: 0 }}>Yangi topshiriq</h3>
          <div className="grid grid-2">
            <div className="field"><label>Oqim</label>
              <select className="input" value={f.cohort} onChange={(e) => setF({ ...f, cohort: +e.target.value })}>
                {data.cohorts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="field"><label>Sana</label><input type="date" className="input" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} required /></div>
          </div>
          <div className="field"><label>Topshiriq</label><input className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Masalan: Kamida 20 bet kitob o'qing" required /></div>
          <div className="field"><label>Tavsif (ixtiyoriy)</label><textarea className="input" rows={2} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="Qanday bajariladi, nimaga e'tibor berish kerak" /></div>
          <div className="field" style={{ maxWidth: 200 }}><label>Mukofot (IrodaCoin)</label><input type="number" min="0" max="1000" className="input" value={f.reward} onChange={(e) => setF({ ...f, reward: +e.target.value })} /></div>
          <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button type="button" className="btn btn-ghost" onClick={() => setF(null)}>Bekor qilish</button>
            <button className="btn btn-primary" disabled={busy || !f.title}>Qo'shish</button>
          </div>
        </form>
      )}
      <div className="stack">
        {data && data.items.length === 0 && !f && (
          <div className="card"><Empty icon={Target} title="Hali topshiriq yo'q" text="Birinchi kunduzgi topshiriqni yozing.">
            <button className="btn btn-primary" onClick={open}><Plus size={16} /> Yangi topshiriq</button>
          </Empty></div>
        )}
        {data?.items.map((b) => (
          <div key={b.id} className="card card-pad">
            <div className="row" style={{ gap: 14, flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 240px", minWidth: 0 }}>
                <div className="row" style={{ gap: 8, marginBottom: 2 }}>
                  <b style={{ fontSize: 16 }}>{b.title}</b>
                  <Pill tone="sun"><Coins size={12} /> {b.reward}</Pill>
                  {b.date === data.today && <Pill tone="ok" dot>Bugun</Pill>}
                </div>
                {b.description && <div className="muted small">{b.description}</div>}
                <div className="muted small" style={{ marginTop: 4 }}>{fmtDate(b.date)} · {b.cohort_name} · <b>{b.done}</b> bajardi</div>
              </div>
              <button className="btn btn-ghost btn-icon" onClick={() => remove(b)} aria-label="O'chirish"><Trash2 size={15} /></button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
