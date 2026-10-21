import {
  AlertTriangle, ArrowRight, Award, CheckCircle2, Clock, Inbox, Shield, ShieldAlert, ShieldCheck,
  UserCheck, UserX, Users, Video,
} from "lucide-react";
import { api } from "../api.js";
import { go } from "../router.js";
import { Avatar, Empty, ErrorBox, PageHead, Pill, Skeleton, TODAY_STATUS, fmtAgo, fmtDate, useLoad } from "../ui.jsx";

function Kpi({ icon: Icon, tone, value, label, to }) {
  return (
    <div className={`card kpi ${to ? "link" : ""}`} onClick={to ? () => go(...to) : undefined} role={to ? "link" : undefined}>
      <div className={`kpi-icon tone-${tone}`}><Icon size={19} /></div>
      <div><b className="num">{value}</b><span>{label}</span></div>
    </div>
  );
}

const SERIES = [
  { key: "done", label: "Bajardi", color: "var(--ok)" },
  { key: "failed", label: "Ogohlantirish", color: "var(--bad)" },
  { key: "rest", label: "Dam / muzlatilgan", color: "var(--info)" },
  { key: "pending", label: "Kutilmoqda", color: "var(--line-strong)" },
];

/** Har bir kun uchun ustma-ust ustunlar: bajardi / ogohlantirish / dam / kutilmoqda. */
function DaysChart({ series, duration, today }) {
  const byDay = Object.fromEntries(series.map((s) => [s.day_number, s]));
  const total = (d) => SERIES.reduce((a, s) => a + (d?.[s.key] || 0), 0);
  const max = Math.max(1, ...series.map(total));
  const W = 640, H = 190, P = 22, gap = 4;
  const bw = (W - P * 2) / duration - gap;
  const h = (v) => (v / max) * (H - 40);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Kunlar bo'yicha bajarish grafigi">
      {[0.5, 1].map((f) => (
        <line key={f} x1={P} x2={W - P} y1={H - 22 - (H - 40) * f} y2={H - 22 - (H - 40) * f} stroke="var(--line)" strokeDasharray="3 4" />
      ))}
      {Array.from({ length: duration }, (_, i) => {
        const day = i + 1;
        const d = byDay[day];
        const x = P + i * (bw + gap);
        let y = H - 22;
        const parts = SERIES.map((s) => {
          const v = d?.[s.key] || 0;
          const hh = h(v);
          y -= hh;
          return v ? <rect key={s.key} x={x} y={y} width={bw} height={hh} fill={s.color} rx={2} /> : null;
        });
        const label = d ? SERIES.filter((s) => d[s.key]).map((s) => `${s.label}: ${d[s.key]}`).join(", ") : "ma'lumot yo'q";
        return (
          <g key={day}>
            <title>{`${day}-kun — ${label}`}</title>
            {!d && <rect x={x} y={H - 26} width={bw} height={4} fill="var(--surface-3)" rx={2} />}
            {parts}
            {(day === 1 || day % 5 === 0 || day === duration || day === today) && (
              <text x={x + bw / 2} y={H - 6} fontSize="10.5" textAnchor="middle" fill={day === today ? "var(--sun-text)" : "var(--muted)"} fontWeight={day === today ? 700 : 400}>
                {day}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function CohortCard({ c }) {
  const pct = c.day ? Math.round((c.day / c.duration) * 100) : 0;
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>{c.name}</h2>
          <p>{fmtDate(c.start_date)} — {fmtDate(c.end_date)} · {c.active} faol · {c.expelled} chiqarilgan</p>
        </div>
        <Pill tone="sun">{c.day ? `${c.day}/${c.duration}-kun` : "boshlanmagan"}</Pill>
      </div>
      <div className="card-pad">
        <div className="progress" style={{ marginBottom: 16 }}><i style={{ width: `${pct}%` }} /></div>
        <DaysChart series={c.series} duration={c.duration} today={c.day} />
        <div className="legend" style={{ marginTop: 8 }}>
          {SERIES.map((s) => <span key={s.key}><i style={{ background: s.color }} />{s.label}</span>)}
        </div>
      </div>
    </div>
  );
}

function SquadMini({ s }) {
  const pct = s.total ? (s.done / s.total) * 100 : 0;
  const tone = pct === 100 ? "ok" : pct >= 50 ? "warn" : "bad";
  return (
    <div className="card card-pad" style={{ cursor: "pointer" }} onClick={() => go("squads")}>
      <div className="row-between" style={{ marginBottom: 8 }}>
        <div><b>{s.squad}</b><div className="muted small">{s.tribe}</div></div>
        <Pill tone={tone}>{s.done}/{s.total}</Pill>
      </div>
      <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
        {s.members.filter((m) => m.status !== "out").map((m) => (
          <span key={m.membership_id} title={`${m.name} — ${TODAY_STATUS[m.status].label}`}
            style={{ width: 12, height: 12, borderRadius: 4, background: `var(--${{ done: "ok", woke: "warn", absent: "bad", frozen: "ice", rest: "info" }[m.status]})` }} />
        ))}
      </div>
    </div>
  );
}

const EVENT_STYLE = {
  new_application: { icon: Inbox, tone: "sun", text: () => "yangi ariza qoldirdi" },
  approved: { icon: UserCheck, tone: "ok", text: (p) => (p.squad ? `qabul qilindi → ${p.squad}` : "qabul qilindi") },
  strike: { icon: ShieldAlert, tone: "bad", text: (p) => `ogohlantirish oldi (${p.count}/${p.max})` },
  expelled: { icon: UserX, tone: "bad", text: () => "lagerdan chiqarildi" },
  stage_up: { icon: Award, tone: "sun", text: (p) => `«${p.name}» bosqichiga chiqdi` },
  immunity_used: { icon: Shield, tone: "info", text: () => "Immunitet bilan qutuldi" },
  immunity_granted: { icon: ShieldCheck, tone: "info", text: () => "Immunitet oldi" },
};

function Events({ items }) {
  if (!items.length) return <Empty icon={Clock} title="Hali voqea yo'q" />;
  return (
    <ul className="events">
      {items.map((e) => {
        const s = EVENT_STYLE[e.kind] || { icon: Clock, tone: "mute", text: () => e.label };
        return (
          <li key={e.id}>
            <div className={`event-icon tone-${s.tone}`}><s.icon size={15} /></div>
            <div style={{ minWidth: 0 }}>
              <div><b>{e.user.name}</b> {s.text(e.payload)}</div>
              <p>{fmtAgo(e.at)}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function PendingApplications({ onChange }) {
  const { data } = useLoad(() => api.applications("pending"));
  const items = data?.items.slice(0, 4) || [];
  return (
    <div className="card">
      <div className="card-head">
        <div><h2>Yangi arizalar</h2><p>Tez ko'rib chiqing</p></div>
        <button className="btn btn-ghost btn-sm" onClick={() => go("applications")}>Hammasi <ArrowRight size={14} /></button>
      </div>
      {data && !items.length && <Empty icon={CheckCircle2} title="Hammasi ko'rib chiqilgan" />}
      <ul className="events">
        {items.map((a) => (
          <li key={a.id} style={{ alignItems: "center", cursor: "pointer" }} onClick={() => { go("applications"); onChange?.(); }}>
            <Avatar name={a.name} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <b>{a.name}</b>
              <p style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{a.current_wake_time} → {a.target_wake_time} · {a.goal}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Dashboard({ onChange }) {
  const { data, error } = useLoad(api.dashboard);
  if (error) return <ErrorBox text={error} />;
  if (!data) {
    return (
      <>
        <Skeleton height={40} style={{ width: 260, marginBottom: 22 }} />
        <div className="kpis">{[0, 1, 2, 3].map((i) => <Skeleton key={i} height={78} />)}</div>
        <Skeleton height={320} />
      </>
    );
  }
  const k = data.kpis;
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Xayrli tong" : hour < 18 ? "Xayrli kun" : "Xayrli kech";

  return (
    <>
      <PageHead title={`${greet}, qo'mondon`} sub={`Bugun ${fmtDate(data.today)} · lagerning bugungi holati`} />

      <div className="kpis">
        <Kpi icon={Users} tone="info" value={k.active} label="Faol ishtirokchilar" to={["members", { status: "active" }]} />
        <Kpi icon={CheckCircle2} tone="ok" value={`${k.done_today}/${k.active}`} label="Bugun raport berdi" to={["squads"]} />
        <Kpi icon={AlertTriangle} tone="warn" value={k.woke_only + k.absent} label="Raport bermaganlar" to={["squads"]} />
        <Kpi icon={Inbox} tone="sun" value={k.pending_applications} label="Yangi arizalar" to={["applications"]} />
      </div>
      <div className="kpis">
        <Kpi icon={ShieldAlert} tone="bad" value={k.strikes_today} label="Bugungi ogohlantirishlar" />
        <Kpi icon={UserX} tone="mute" value={k.expelled_total} label="Chiqarilganlar (oqimda)" to={["members", { status: "expelled" }]} />
        <Kpi icon={Video} tone="info" value={k.videos_reviewing} label="Tekshiruvdagi videolar" to={["videos"]} />
        <Kpi icon={Clock} tone="mute" value={`${data.rules.voice_deadline} daq`} label="Raport muddati" to={["settings"]} />
      </div>

      <div className="grid grid-main">
        <div className="stack">
          {data.cohorts.length ? data.cohorts.map((c) => <CohortCard key={c.id} c={c} />) : (
            <div className="card"><Empty icon={Clock} title="Davom etayotgan oqim yo'q" text="Yangi oqim oching va qabulni boshlang.">
              <button className="btn btn-primary" onClick={() => go("cohorts")}>Oqimlar</button>
            </Empty></div>
          )}
          {data.squads.length > 0 && (
            <div>
              <div className="row-between" style={{ margin: "4px 2px 12px" }}>
                <h2>Rotalar — bugungi raport</h2>
                <button className="btn btn-ghost btn-sm" onClick={() => go("squads")}>Batafsil <ArrowRight size={14} /></button>
              </div>
              <div className="squad-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(210px, 1fr))" }}>
                {data.squads.map((s) => <SquadMini key={s.id} s={s} />)}
              </div>
            </div>
          )}
        </div>
        <div className="stack">
          <PendingApplications onChange={onChange} />
          <div className="card">
            <div className="card-head"><div><h2>So'nggi voqealar</h2><p>Lagerdagi harakatlar</p></div></div>
            <Events items={data.events} />
          </div>
          {data.recruiting.length > 0 && (
            <div className="card card-pad">
              <h3 style={{ marginBottom: 8 }}>Qabul ochiq</h3>
              {data.recruiting.map((r) => (
                <div key={r.id} className="row-between small" style={{ padding: "4px 0" }}>
                  <span><b>{r.name}</b> · start {fmtDate(r.start_date)}</span><Pill tone="sun">{r.members} kishi</Pill>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
