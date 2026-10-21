import {
  ArrowRightLeft, Award, Crown, RotateCcw, ShieldAlert, ShieldCheck, Target, Undo2, UserX,
} from "lucide-react";
import { api } from "../api.js";
import {
  Drawer, MEMBER_STATUS, Person, Pill, Skeleton, StatusPill, StrikeDots, TODAY_STATUS, fmtDate, useAction, useConfirm, useLoad,
} from "../ui.jsx";

const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const DAY_LABEL = { completed: "bajarildi", failed: "bajarilmadi — bosib uzrli qilish mumkin", rest: "yakshanba", frozen: "muzlatilgan", pending: "kutilmoqda", future: "hali kelmagan" };

function Stat({ value, label }) {
  return (
    <div className="card card-pad" style={{ padding: "12px 14px" }}>
      <b className="num" style={{ fontSize: 20, display: "block" }}>{value}</b>
      <span className="muted small">{label}</span>
    </div>
  );
}

export default function MemberDrawer({ id, onClose, onChanged }) {
  const confirm = useConfirm();
  const { data: m, reload } = useLoad(() => api.member(id), [id]);
  const [run, busy] = useAction(async () => { await reload(); onChanged?.(); });
  const act = (body, ask) => async () => {
    if (ask && !(await confirm(ask))) return;
    run(() => api.memberAction(id, body));
  };

  const title = m ? (
    <div className="row" style={{ gap: 12 }}>
      <Person user={m.user} sub={`${m.squad?.name || "—"} · ${m.tribe}`} />
      <StatusPill map={MEMBER_STATUS} value={m.status} />
    </div>
  ) : <Skeleton height={36} style={{ width: 220 }} />;

  return (
    <Drawer onClose={onClose} title={title}>
      {!m ? <Skeleton height={400} /> : (
        <div className="stack">
          <div className="grid grid-3" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
            <Stat value={m.journey.current_day ? `${m.journey.current_day}/${m.journey.duration}` : "—"} label="Kun" />
            <Stat value={m.journey.survived} label="O'tgan kunlar" />
            <Stat value={<StrikeDots count={m.strikes} max={m.journey.rules.max_strikes} />} label="Ogohlantirish" />
            <Stat value={m.immunities} label="Immunitet" />
          </div>

          <div className="card card-pad">
            <div className="row-between" style={{ marginBottom: 10 }}>
              <div className="row" style={{ gap: 8 }}>
                <Award size={16} color="var(--sun)" />
                <b>{m.journey.stage ? m.journey.stage.name : "Bosqich hali yo'q"}</b>
              </div>
              <StatusPill map={TODAY_STATUS} value={m.today} />
            </div>
            <div className="row small muted" style={{ gap: 16, flexWrap: "wrap" }}>
              <span>Budilnik: <b className="num" style={{ color: "var(--text)" }}>{m.start_wake_time} → {m.target_wake_time}</b></span>
              <span>Qo'shilgan: {fmtDate(m.joined_at)}</span>
              <span>Oqim: {m.cohort.name}</span>
              {m.user.region && <span>Viloyat: {m.user.region}</span>}
            </div>
            {m.goal && (
              <div className="row" style={{ alignItems: "flex-start", gap: 8, marginTop: 12, padding: "10px 12px", background: "var(--surface-2)", borderRadius: 10 }}>
                <Target size={15} style={{ marginTop: 2, color: "var(--sun)", flex: "none" }} />
                <span style={{ fontStyle: "italic" }}>{m.goal}</span>
              </div>
            )}
          </div>

          <div className="card card-pad">
            <h3 style={{ marginBottom: 10 }}>{m.journey.duration} kunlik kalendar</h3>
            <div className="cal" style={{ marginBottom: 6 }}>
              {WEEKDAYS.map((w) => <span key={w} className="muted small" style={{ textAlign: "center", fontWeight: 600 }}>{w}</span>)}
            </div>
            <div className="cal">
              {Array.from({ length: m.journey.days[0]?.weekday || 0 }, (_, i) => <span key={`e${i}`} />)}
              {m.journey.days.map((d) => (
                <button
                  key={d.day_number} type="button"
                  className={`cal-day ${d.status} ${d.today ? "today" : ""}`}
                  title={`${d.day_number}-kun · ${d.date} · budilnik ${d.alarm_time} · ${DAY_LABEL[d.status] || d.status}`}
                  onClick={d.status === "failed" ? act({ action: "excuse_day", day_number: d.day_number }, {
                    title: `${d.day_number}-kunni uzrli qilasizmi?`,
                    text: "Kun bajarilgan deb belgilanadi va shu kun uchun berilgan ogohlantirish bekor qilinadi.",
                    confirm: "Uzrli qilish",
                  }) : undefined}
                >
                  {d.day_number}
                </button>
              ))}
            </div>
          </div>

          <div className="card card-pad">
            <h3 style={{ marginBottom: 12 }}>Amallar</h3>
            <div className="grid grid-2" style={{ gap: 8 }}>
              <button className="btn btn-outline" disabled={busy} onClick={act({ action: "give_immunity" })}><ShieldCheck size={16} /> Immunitet berish</button>
              <button className="btn btn-outline" disabled={busy || m.status !== "active"} onClick={act({ action: "give_strike" }, {
                title: "Ogohlantirish berasizmi?", text: `${m.user.name} ga qo'mondonlik qarori bilan ogohlantirish beriladi (Immunitet ishlatilmaydi).`, confirm: "Berish", danger: true,
              })}><ShieldAlert size={16} /> Ogohlantirish berish</button>
              {m.status === "active" ? (
                <button className="btn btn-bad" disabled={busy} onClick={act({ action: "expel" }, {
                  title: "Lagerdan chiqarasizmi?", text: `${m.user.name} lagerdan chiqariladi va rota guruhidan haydaladi.`, confirm: "Chiqarish", danger: true,
                })}><UserX size={16} /> Lagerdan chiqarish</button>
              ) : (
                <button className="btn btn-outline" disabled={busy} onClick={act({ action: "restore" })}><Undo2 size={16} /> Lagerga qaytarish</button>
              )}
              <button className="btn btn-outline" disabled={busy || m.status === "mentor"} onClick={act({ action: "mentor" })}><Crown size={16} /> Mentor qilish</button>
            </div>
            {m.squads.length > 1 && (
              <div className="row" style={{ marginTop: 12 }}>
                <ArrowRightLeft size={16} className="muted" />
                <span className="small muted">Rota:</span>
                <select className="select" style={{ width: "auto" }} value={m.squad?.id || ""} disabled={busy}
                  onChange={(e) => run(() => api.memberAction(id, { action: "move_squad", squad_id: Number(e.target.value) }))}>
                  {m.squads.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-head"><h3>Ogohlantirishlar</h3><span className="muted small">{m.strikes_list.length} ta</span></div>
            {!m.strikes_list.length && <div className="card-pad muted small">Ogohlantirish yo'q.</div>}
            <ul className="events">
              {m.strikes_list.map((s) => (
                <li key={s.id} style={{ alignItems: "center" }}>
                  <div className={`event-icon tone-${s.revoked || s.immunity ? "mute" : "bad"}`}><ShieldAlert size={15} /></div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ textDecoration: s.revoked || s.immunity ? "line-through" : "none" }}><b>{s.reason}</b>{s.day && ` · ${s.day}-kun`}</div>
                    <p>{fmtDate(s.at)}{s.revoked && " · bekor qilingan"}{s.immunity && " · Immunitet bilan o'chirilgan"}</p>
                  </div>
                  {!s.revoked && !s.immunity && (
                    <button className="btn btn-ghost btn-sm" disabled={busy} onClick={act({ action: "revoke_strike", strike_id: s.id })}><RotateCcw size={14} /> Bekor qilish</button>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {m.awards.length > 0 && (
            <div className="card">
              <div className="card-head"><h3>Mukofotlar</h3><span className="muted small">{m.awards.length} ta</span></div>
              <div className="card-pad award-grid">
                {m.awards.map((a) => (
                  <a key={a.id} href={api.awardUrl(a.id)} target="_blank" rel="noreferrer" title={`${a.stage} · ${a.award} · ${a.number}`}>
                    <img src={api.awardUrl(a.id)} alt={`${a.stage} mukofoti`} />
                  </a>
                ))}
              </div>
            </div>
          )}

          {m.immunities_list.length > 0 && (
            <div className="card">
              <div className="card-head"><h3>Immunitetlar</h3></div>
              <ul className="events">
                {m.immunities_list.map((i) => (
                  <li key={i.id} style={{ alignItems: "center" }}>
                    <div className={`event-icon tone-${i.used ? "mute" : "info"}`}><ShieldCheck size={15} /></div>
                    <div style={{ flex: 1 }}><b>{i.source}</b><p>{fmtDate(i.at)}</p></div>
                    <Pill tone={i.used ? "mute" : "info"}>{i.used ? "ishlatilgan" : "mavjud"}</Pill>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}
