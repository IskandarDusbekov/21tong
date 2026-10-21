// "Yo'l" — 4 bosqich, 21 kunlik kalendar va Kaizen budilnik grafigi.
import { BedDouble, Check, Crown, Flame, Medal, Mountain, Shield, Snowflake, Sprout, Star, TrendingDown, X } from "lucide-react";
import { useEffect, useState } from "react";
import { awardImage } from "../api.js";
import { Empty, ErrorCard, Skeleton } from "../ui.jsx";

// Bosqich ikonkalari admin panelda tanlanadi (control.Stage.icon)
export const STAGE_ICONS = { sprout: Sprout, mountain: Mountain, shield: Shield, crown: Crown, flame: Flame, star: Star, medal: Medal };
export const stageIcon = (s) => STAGE_ICONS[s?.icon] || Star;


const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];

const DAY_ICON = { completed: Check, failed: X, rest: BedDouble, frozen: Snowflake };

function NextStage({ j }) {
  const next = j.next_stage;
  if (!next) {
    return (
      <div className="card next-stage">
        <div className="stage-badge" style={{ background: "linear-gradient(135deg, var(--sun-2), var(--sun))", color: "#fff", border: 0 }}><Crown size={22} /></div>
        <div><b>Barcha bosqichlar zabt etildi</b><p className="small muted" style={{ margin: 0 }}>Siz endi Mentorsiz.</p></div>
      </div>
    );
  }
  const prevDay = [...j.stages].reverse().find((s) => s.reached)?.day || 0;
  const pct = ((j.survived - prevDay) / (next.day - prevDay)) * 100;
  const Icon = stageIcon(next);
  return (
    <div className="card">
      <div className="next-stage">
        <div className="stage-badge" style={{ borderColor: "var(--sun)", color: "var(--sun)", borderStyle: "dashed" }}><Icon size={22} /></div>
        <div style={{ flex: 1 }}>
          <small className="muted">Keyingi bosqich</small>
          <b style={{ display: "block", fontSize: 17 }}>{next.name}</b>
        </div>
        <div style={{ textAlign: "right" }}>
          <b className="num" style={{ fontSize: 22 }}>{next.day - j.survived}</b>
          <small className="muted" style={{ display: "block" }}>kun qoldi</small>
        </div>
      </div>
      <div className="progress"><i style={{ width: `${Math.max(pct, 3)}%` }} /></div>
      <small className="muted num">{j.survived} / {next.day} kun</small>
    </div>
  );
}

function Stages({ j }) {
  return (
    <ol className="stages card">
      {j.stages.map((s) => {
        const Icon = stageIcon(s);
        const isNext = j.next_stage?.day === s.day;
        return (
          <li key={s.day} className={`stage ${s.reached ? "reached" : ""} ${isNext ? "next" : ""}`}>
            <div className="stage-badge"><Icon size={20} /></div>
            <div className="stage-body">
              <b>{s.day}-kun · {s.name}</b>
              <p>{s.description}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function Calendar({ days }) {
  const lead = days.length ? days[0].weekday : 0; // birinchi kun haftaning qaysi kuni
  return (
    <div className="card">
      <div className="cal-head">{WEEKDAYS.map((w) => <span key={w}>{w}</span>)}</div>
      <div className="cal">
        {Array.from({ length: lead }, (_, i) => <div key={`e${i}`} className="cal-day empty" />)}
        {days.map((d) => {
          const Icon = DAY_ICON[d.status];
          return (
            <div
              key={d.day_number}
              className={`cal-day ${d.status} ${d.today ? "today" : ""}`}
              title={`${d.day_number}-kun · ${d.date} · ${d.alarm_time}`}
            >
              <span className="num">{d.day_number}</span>
              {Icon && <Icon size={10} strokeWidth={3} />}
            </div>
          );
        })}
      </div>
      <div className="legend">
        <span><i style={{ background: "var(--ok)" }} />Bajarildi</span>
        <span><i style={{ background: "var(--bad)" }} />Ogohlantirish</span>
        <span><i style={{ background: "var(--rest)" }} />Yakshanba</span>
        <span><i style={{ background: "var(--ice)" }} />Muzlatilgan</span>
      </div>
    </div>
  );
}

function AwardCard({ a }) {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    let url;
    awardImage(a.id).then((u) => { url = u; setSrc(u); }).catch(() => {});
    return () => url && URL.revokeObjectURL(url);
  }, [a.id]);
  return (
    <a className="award" href={src || undefined} target="_blank" rel="noreferrer">
      {src ? <img src={src} alt={`${a.stage} — ${a.award}`} /> : <div className="skeleton" style={{ aspectRatio: "4 / 5" }} />}
      <b>{a.rank || a.stage}</b>
      <small className="muted">{a.day}-kun · {a.award.split(" (")[0]}</small>
    </a>
  );
}

function Awards({ items }) {
  return <div className="awards">{items.map((a) => <AwardCard key={a.id} a={a} />)}</div>;
}

const toMin = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };

function KaizenChart({ days, rules, target }) {
  const W = 320, H = 120, P = 8;
  const values = days.map((d) => toMin(d.alarm_time));
  const max = Math.max(...values), min = Math.min(...values, toMin(target));
  const span = Math.max(max - min, 1);
  const x = (i) => P + (i * (W - 2 * P)) / (days.length - 1);
  const y = (v) => P + ((max - v) / span) * (H - 2 * P - 14);
  const path = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const todayIdx = days.findIndex((d) => d.today);
  return (
    <div className="card kaizen">
      <div className="next-stage" style={{ marginBottom: 10 }}>
        <div className="stat-icon" style={{ background: "var(--sun-soft)", color: "var(--sun)", margin: 0 }}><TrendingDown size={17} /></div>
        <div style={{ flex: 1 }}>
          <b>Kaizen: budilnik yo'li</b>
          <small className="muted" style={{ display: "block" }}>{rules.shift_from_day}-kundan har kuni −{rules.shift_minutes} daqiqa</small>
        </div>
        <b className="num">{days[0].alarm_time} → {target}</b>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Budilnik vaqtining kunlar bo'yicha o'zgarishi">
        <defs>
          <linearGradient id="kz-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--sun)" stopOpacity=".28" />
            <stop offset="1" stopColor="var(--sun)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <line x1={P} x2={W - P} y1={y(toMin(target))} y2={y(toMin(target))} stroke="var(--line)" strokeDasharray="4 4" />
        <path d={`${path} L${x(days.length - 1)},${H - 14} L${x(0)},${H - 14} Z`} fill="url(#kz-fill)" />
        <path d={path} fill="none" stroke="var(--sun)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {todayIdx >= 0 && (
          <g>
            <circle cx={x(todayIdx)} cy={y(values[todayIdx])} r="6" fill="var(--sun)" opacity=".25" />
            <circle cx={x(todayIdx)} cy={y(values[todayIdx])} r="3.5" fill="var(--sun)" stroke="var(--surface)" strokeWidth="1.5" />
          </g>
        )}
        {[0, rules.shift_from_day - 1, days.length - 1].map((i) => (
          <text key={i} x={x(i)} y={H - 1} fontSize="10" fill="var(--muted)" textAnchor={i === 0 ? "start" : i === days.length - 1 ? "end" : "middle"}>
            {i + 1}-kun
          </text>
        ))}
      </svg>
      <p className="small muted" style={{ margin: "8px 2px 0" }}>
        Erta turish birdan emas — har kuni atigi {rules.shift_minutes} daqiqa erta. Shuning uchun tanangiz qiynalmaydi:
        {" "}{days[0].alarm_time} dan boshlab {target} ga silliq tushasiz.
      </p>
    </div>
  );
}

export default function Journey({ me, error }) {
  if (error && !me) return <ErrorCard text={error} />;
  if (!me) return <div className="stack"><Skeleton height={110} /><Skeleton height={300} /></div>;
  const j = me.journey;
  if (!j) return <Empty icon={Sprout} title="Yo'l oqim boshlangach ochiladi" text="Botda /join orqali oqimga qo'shiling." />;

  return (
    <div>
      <div className="screen-head">
        <div>
          <h2>Sizning yo'lingiz</h2>
          <p className="muted small">{j.survived} kun ortda · {j.duration} kunlik lager</p>
        </div>
      </div>
      <NextStage j={j} />
      {me.awards?.length > 0 && (
        <>
          <div className="section-title">Mukofotlarim</div>
          <Awards items={me.awards} />
        </>
      )}
      <div className="section-title">21 kun</div>
      <Calendar days={j.days} />
      <div className="section-title">Bosqichlar</div>
      <Stages j={j} />
      <div className="section-title">Uyg'onish vaqti</div>
      <KaizenChart days={j.days} rules={j.rules} target={me.membership.target_wake_time} />
      {me.goal && (
        <>
          <div className="section-title">Manifest</div>
          <div className="card quote" style={{ marginTop: 0, fontSize: 15 }}>“{me.goal}”</div>
        </>
      )}
    </div>
  );
}
