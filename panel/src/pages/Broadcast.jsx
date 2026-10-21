import { useEffect, useState } from "react";
import { History, Megaphone, Send, Users } from "lucide-react";
import { api } from "../api.js";
import { Empty, ErrorBox, PageHead, Pill, Seg, Skeleton, TgBubble, fmtAgo, useAction, useConfirm, useLoad } from "../ui.jsx";

const GENDER_LABEL = { "": "hammaga", M: "yigitlarga", F: "qizlarga" };

export default function Broadcast() {
  const confirm = useConfirm();
  const { data, error, reload } = useLoad(api.broadcasts);
  const [f, setF] = useState({ audience: "active", cohort: "", squad: "", gender: "", text: "" });
  const [count, setCount] = useState(null);
  const [run, busy] = useAction(async () => { await reload(); setF((x) => ({ ...x, text: "" })); });

  const body = { ...f, cohort: f.cohort || null, squad: f.squad || null };
  const needsCohort = f.audience === "cohort" && !f.cohort;
  const needsSquad = f.audience === "squad" && !f.squad;

  useEffect(() => {
    if (needsCohort || needsSquad) return setCount(null);
    const t = setTimeout(() => {
      api.previewBroadcast({ ...body, text: body.text || "." }).then((r) => setCount(r.recipients)).catch(() => setCount(null));
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [f.audience, f.cohort, f.squad, f.gender]);

  const send = async () => {
    const ok = await confirm({
      title: `${count} kishiga yuborilsinmi?`,
      text: "Xabar bot orqali darhol yuboriladi. Yuborilganini qaytarib bo'lmaydi.",
      confirm: "Yuborish",
    });
    if (ok) run(() => api.sendBroadcast(body));
  };

  return (
    <>
      <PageHead title="Ommaviy xabar" sub="Bot orqali ishtirokchilarga e'lon yuborish." />
      {error && <ErrorBox text={error} />}
      {!data ? <Skeleton height={400} /> : (
        <div className="grid grid-main">
          <div className="card">
            <div className="card-head"><div><h2>Yangi xabar</h2><p>Kimga va nima yuborilishini tanlang</p></div></div>
            <div className="card-pad stack">
              <div className="field">
                <label>Kimga</label>
                <select className="select" value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })}>
                  {data.audiences.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                </select>
              </div>
              {f.audience === "cohort" && (
                <div className="field"><label>Oqim</label>
                  <select className="select" value={f.cohort} onChange={(e) => setF({ ...f, cohort: e.target.value })}>
                    <option value="">— tanlang —</option>
                    {data.cohorts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
              )}
              {f.audience === "squad" && (
                <div className="field"><label>Rota</label>
                  <select className="select" value={f.squad} onChange={(e) => setF({ ...f, squad: e.target.value })}>
                    <option value="">— tanlang —</option>
                    {data.squads.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
              )}
              <div className="field">
                <label>Jins</label>
                <Seg value={f.gender} onChange={(g) => setF({ ...f, gender: g })} options={[{ value: "", label: "Hammaga" }, { value: "M", label: "Faqat yigitlar" }, { value: "F", label: "Faqat qizlar" }]} />
              </div>
              <div className="field">
                <label>Xabar</label>
                <textarea className="textarea" style={{ fontFamily: "inherit", fontSize: 14, minHeight: 150 }} value={f.text}
                  onChange={(e) => setF({ ...f, text: e.target.value })} placeholder="Masalan: Ertaga yakshanba — dam olish kuni. Barvaqt turganlar Immunitet oladi!" />
                <div className="hint">Formatlash: &lt;b&gt;qalin&lt;/b&gt;, &lt;i&gt;kursiv&lt;/i&gt;, &lt;blockquote&gt;iqtibos&lt;/blockquote&gt;</div>
              </div>
              <div className="row-between" style={{ flexWrap: "wrap" }}>
                <span className="row muted" style={{ gap: 6 }}>
                  <Users size={16} />
                  {needsCohort || needsSquad ? "Avval tanlang" : count == null ? "…" : <><b style={{ color: "var(--text)" }}>{count}</b> kishi oladi ({GENDER_LABEL[f.gender]})</>}
                </span>
                <button className="btn btn-primary" disabled={busy || !f.text.trim() || !count} onClick={send}><Send size={16} /> Yuborish</button>
              </div>
            </div>
          </div>

          <div className="stack">
            <div className="card">
              <div className="card-head"><h3>Telegram'da shunday ko'rinadi</h3></div>
              <div className="card-pad">
                <div className="tg-preview"><TgBubble html={f.text || "Xabar matni shu yerda ko'rinadi…"} /></div>
              </div>
            </div>
            <div className="card">
              <div className="card-head"><div className="row" style={{ gap: 8 }}><History size={16} /><h3>Yuborilganlar</h3></div></div>
              {!data.items.length && <Empty icon={Megaphone} title="Hali xabar yuborilmagan" />}
              <ul className="events">
                {data.items.map((b) => (
                  <li key={b.id}>
                    <div className="event-icon tone-sun"><Megaphone size={15} /></div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{b.text.replace(/<[^>]+>/g, "")}</div>
                      <p>{b.audience_label}{b.gender && ` · ${GENDER_LABEL[b.gender]}`} · {fmtAgo(b.created_at)}</p>
                    </div>
                    <Pill tone="ok">{b.sent_count}</Pill>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
