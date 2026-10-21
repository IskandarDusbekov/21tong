// Reyting — 3 daraja: rotam ichidagi shaxslar, rotalar o'rtasida, qabila eng zo'rlari.
// Ball = bajarilgan kun·10 + IrodaCoin + rasm chelenjidagi 🔥·5.
import { useState } from "react";
import { Coins, Flame, Trophy, Users } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorCard, Skeleton, useLoad } from "../ui.jsx";

const MEDAL = ["#f2b705", "#b8c0cc", "#cd7f32"];

function Podium({ top }) {
  const order = [top[1], top[0], top[2]];
  const places = [2, 1, 3];
  return (
    <div className="podium">
      {order.map((r, i) =>
        r ? (
          <div key={places[i]} className={`podium-col ${places[i] === 1 ? "first" : ""}`}>
            <Avatar name={r.name} />
            <div className="podium-name">{r.name}{r.me && " (siz)"}</div>
            <div className="podium-bar" style={{ background: `linear-gradient(180deg, ${MEDAL[places[i] - 1]}, color-mix(in srgb, ${MEDAL[places[i] - 1]} 60%, #0000))` }}>
              <div style={{ fontSize: 20 }}>{places[i]}</div>
              <small className="num" style={{ color: "#fff" }}>{r.points}</small>
            </div>
          </div>
        ) : <div key={places[i]} />,
      )}
    </div>
  );
}

function PersonRow({ r, pos }) {
  return (
    <li className={r.me ? "me" : ""}>
      <span className="pos num">{pos}</span>
      <Avatar name={r.name} />
      <div className="rank-main">
        <span className="name">{r.name}{r.me && " (siz)"}</span>
        <small className="muted rank-sub">
          {r.days} kun · <span className="num"><Coins size={11} />{r.coins}</span> · <span className="num"><Flame size={11} />{r.votes}</span>
        </small>
      </div>
      <b className="num points">{r.points}</b>
    </li>
  );
}

function People({ rows }) {
  if (!rows.length) return <Empty icon={Trophy} title="Hali ball yo'q" text="Raport bering, topshiriq va rasm chelenjida qatnashing." />;
  return (
    <>
      {rows.length >= 3 && <Podium top={rows.slice(0, 3)} />}
      <ol className="rank-list card">
        {(rows.length >= 3 ? rows.slice(3) : rows).map((r, i) => (
          <PersonRow key={r.id} r={r} pos={rows.length >= 3 ? i + 4 : i + 1} />
        ))}
      </ol>
    </>
  );
}

function Squads({ rows }) {
  if (!rows.length) return <Empty icon={Users} title="Rotalar hali yo'q" />;
  return (
    <ol className="rank-list card">
      {rows.map((s) => (
        <li key={s.squad_id} className={s.me ? "me" : ""}>
          <span className="pos num" style={{ color: s.rank <= 3 ? MEDAL[s.rank - 1] : undefined }}>{s.rank}</span>
          <div className="squad-badge"><Users size={16} /></div>
          <div className="rank-main">
            <span className="name">{s.squad}{s.me && " (siz)"}</span>
            <small className="muted rank-sub">{s.members} kishi · o'rtacha {s.avg}</small>
          </div>
          <b className="num points">{s.points}</b>
        </li>
      ))}
    </ol>
  );
}

const TABS = [
  { id: "squad", label: "Rotam", icon: Users },
  { id: "squads", label: "Rotalar", icon: Trophy },
  { id: "tribe", label: "Eng zo'rlar", icon: Flame },
];

export default function Rating() {
  const { data, error } = useLoad(api.ranking);
  const [tab, setTab] = useState("squad");

  return (
    <div>
      <div className="screen-head">
        <div>
          <h2>Reyting</h2>
          <p className="muted small">Ball = kun·10 + IrodaCoin + rasm 🔥·5</p>
        </div>
        <div className="window-icon" style={{ background: "var(--sun-soft)", color: "var(--sun)" }}><Trophy size={18} /></div>
      </div>

      <div className="seg">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {error && !data && <ErrorCard text={error} />}
      {!data && !error && <Skeleton height={260} />}
      {data && (
        <>
          {tab === "squad" && <People rows={data.squad} />}
          {tab === "squads" && <Squads rows={data.squads} />}
          {tab === "tribe" && <People rows={data.tribe_top} />}
        </>
      )}
    </div>
  );
}
