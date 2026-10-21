import { useState } from "react";
import { AlarmClock, Check, Gift, Inbox, MapPin, Target, X } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorBox, GENDER, PageHead, Pill, Seg, Skeleton, fmtAgo, useAction, useConfirm, useLoad } from "../ui.jsx";

const STATUS_TONE = { pending: "sun", approved: "ok", rejected: "bad", new: "mute" };

function ApplicationCard({ a, onDone }) {
  const confirm = useConfirm();
  const [run, busy] = useAction(onDone);
  const approve = () => run(() => api.decide(a.id, "approve"), (r) => (r.placed ? `${a.name} qabul qilindi → ${r.placed}` : `${a.name} qabul qilindi. Qabul ochiq oqim yo'q — oqim ochilganda joylashadi.`));
  const reject = async () => {
    if (await confirm({ title: "Arizani rad etasizmi?", text: `${a.name} ga rad javobi yuboriladi.`, confirm: "Rad etish", danger: true })) {
      run(() => api.decide(a.id, "reject"), `${a.name} arizasi rad etildi.`);
    }
  };
  return (
    <div className="card card-pad">
      <div className="row" style={{ alignItems: "flex-start", gap: 14 }}>
        <Avatar name={a.name} size={44} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
            <h2>{a.name}</h2>
            {a.username && <span className="muted">@{a.username}</span>}
            <Pill tone={a.gender === "F" ? "info" : "mute"}>{GENDER[a.gender] || "—"}</Pill>
            {a.region && <Pill><MapPin size={11} /> {a.region}</Pill>}
            {a.status !== "pending" && <Pill tone={STATUS_TONE[a.status]} dot>{a.status_label}</Pill>}
          </div>
          <div className="row small muted" style={{ flexWrap: "wrap", gap: 14, marginTop: 6 }}>
            <span className="row" style={{ gap: 5 }}><AlarmClock size={14} /> <b style={{ color: "var(--text)" }} className="num">{a.current_wake_time || "—"}</b> → <b style={{ color: "var(--sun-text)" }} className="num">{a.target_wake_time || "—"}</b></span>
            {a.slot_cohort && <span>rota: {a.slot_cohort}</span>}
            {a.referred_by && <span className="row" style={{ gap: 5 }}><Gift size={14} /> taklif qilgan: {a.referred_by}</span>}
            <span>{fmtAgo(a.created_at)}</span>
          </div>
          {a.goal && (
            <div className="row" style={{ alignItems: "flex-start", gap: 8, marginTop: 12, padding: "10px 12px", background: "var(--surface-2)", borderRadius: 10 }}>
              <Target size={15} style={{ marginTop: 2, color: "var(--sun)", flex: "none" }} />
              <span style={{ fontStyle: "italic" }}>{a.goal}</span>
            </div>
          )}
        </div>
        {a.status === "pending" && (
          <div className="row" style={{ flexDirection: "column", gap: 8 }}>
            <button className="btn btn-ok" disabled={busy} onClick={approve}><Check size={16} /> Qabul</button>
            <button className="btn btn-bad" disabled={busy} onClick={reject}><X size={16} /> Rad</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Applications({ onChange }) {
  const [status, setStatus] = useState("pending");
  const { data, error, reload } = useLoad(() => api.applications(status), [status]);
  const counts = data?.counts || {};
  const done = async () => { await reload(); onChange?.(); };

  return (
    <>
      <PageHead title="Arizalar" sub="Botda qoldirilgan arizalar. Qabul qilingan odam qabul ochiq oqimga va rotaga o'zi joylashadi.">
        <Seg value={status} onChange={setStatus} options={[
          { value: "pending", label: "Kutilmoqda", count: counts.pending || 0 },
          { value: "approved", label: "Qabul qilingan", count: counts.approved || 0 },
          { value: "rejected", label: "Rad etilgan", count: counts.rejected || 0 },
          { value: "all", label: "Hammasi" },
        ]} />
      </PageHead>
      {error && <ErrorBox text={error} />}
      {!data && !error && <div className="stack">{[0, 1, 2].map((i) => <Skeleton key={i} height={130} />)}</div>}
      {data && !data.items.length && (
        <div className="card"><Empty icon={Inbox} title={status === "pending" ? "Yangi ariza yo'q" : "Bu yerda hech kim yo'q"} text="Yangi arizalar botdan shu yerga tushadi." /></div>
      )}
      <div className="stack">{data?.items.map((a) => <ApplicationCard key={a.id} a={a} onDone={done} />)}</div>
    </>
  );
}
