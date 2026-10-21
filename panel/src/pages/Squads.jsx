import { useState } from "react";
import { BedDouble, CheckCircle2, Hourglass, Snowflake, UserX, UsersRound, XCircle } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorBox, PageHead, Pill, Seg, Skeleton, TODAY_STATUS, useLoad } from "../ui.jsx";
import MemberDrawer from "./MemberDrawer.jsx";

const STATUS_ICON = {
  done: [CheckCircle2, "var(--ok)"], woke: [Hourglass, "var(--warn)"], absent: [XCircle, "var(--bad)"],
  frozen: [Snowflake, "var(--ice)"], rest: [BedDouble, "var(--info)"], out: [UserX, "var(--muted)"],
};

function SquadCard({ s, onOpen }) {
  const pct = s.total ? Math.round((s.done / s.total) * 100) : 0;
  return (
    <div className="card squad-card">
      <div className="card-head">
        <div style={{ minWidth: 0 }}>
          <h2>{s.squad}</h2>
          <p>{s.tribe} · {s.cohort}</p>
        </div>
        <Pill tone={pct === 100 ? "ok" : pct >= 50 ? "warn" : "bad"}>{s.done}/{s.total}</Pill>
      </div>
      <div style={{ padding: "12px 18px 0" }}>
        <div className="progress"><i style={{ width: `${pct}%`, background: "linear-gradient(90deg, #4fd28f, var(--ok))" }} /></div>
      </div>
      <ul className="members">
        {s.members.map((m) => {
          const [Icon, color] = STATUS_ICON[m.status];
          return (
            <li key={m.membership_id} className={m.status === "out" ? "out" : ""} onClick={() => onOpen(m.membership_id)} title={TODAY_STATUS[m.status].label}>
              <Avatar name={m.name} />
              <span className="name">{m.name}</span>
              {m.strikes > 0 && m.status !== "out" && <span className="pill tone-bad">{m.strikes}</span>}
              <Icon size={17} color={color} />
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function Squads() {
  const [gender, setGender] = useState("");
  const [open, setOpen] = useState(null);
  const { data, error, reload } = useLoad(api.squads);
  const items = data?.filter((s) => !gender || s.gender === gender);
  const done = items?.reduce((a, s) => a + s.done, 0) || 0;
  const total = items?.reduce((a, s) => a + s.total, 0) || 0;

  return (
    <>
      <PageHead title="Rotalar" sub={data ? `${items.length} ta rota · bugun ${done}/${total} kishi raport berdi` : "…"}>
        <Seg value={gender} onChange={setGender} options={[{ value: "", label: "Hammasi" }, { value: "M", label: "Yigitlar" }, { value: "F", label: "Qizlar" }]} />
      </PageHead>
      <div className="legend" style={{ marginBottom: 14 }}>
        {Object.entries(STATUS_ICON).map(([k, [Icon, color]]) => (
          <span key={k}><Icon size={14} color={color} /> {TODAY_STATUS[k].label}</span>
        ))}
      </div>
      {error && <ErrorBox text={error} />}
      {!data && !error && <div className="squad-grid">{[0, 1, 2].map((i) => <Skeleton key={i} height={360} />)}</div>}
      {items && !items.length && <div className="card"><Empty icon={UsersRound} title="Rota yo'q" text="Arizalar qabul qilinganda rotalar o'zi ochiladi." /></div>}
      <div className="squad-grid">{items?.map((s) => <SquadCard key={s.id} s={s} onOpen={setOpen} />)}</div>
      {open && <MemberDrawer id={open} onClose={() => setOpen(null)} onChanged={reload} />}
    </>
  );
}
