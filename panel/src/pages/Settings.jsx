import { useEffect, useMemo, useState } from "react";
import { AlarmClock, Calendar, Coins, Lightbulb, RotateCcw, Save, Shield, TrendingDown, Users } from "lucide-react";
import { api } from "../api.js";
import { ErrorBox, PageHead, Skeleton, Stepper, Switch, useAction, useLoad } from "../ui.jsx";

const ICONS = { "alarm-clock": AlarmClock, "trending-down": TrendingDown, shield: Shield, users: Users, calendar: Calendar, coins: Coins };

const toMin = (t) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
const fromMin = (m) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;

/** Sozlamalar amalda qanday ishlashini oddiy misol bilan ko'rsatadi. */
function Example({ v }) {
  const start = 7 * 60, target = 5 * 60 + 30;
  const alarm = (day) => (day < v.shift_from_day ? start : Math.max(target, start - v.shift_step_minutes * (day - v.shift_from_day + 1)));
  const reachDay = Array.from({ length: 120 }, (_, i) => i + 1).find((d) => alarm(d) === target);
  const video = v.video_from_day > 0;
  return (
    <div className="card card-pad" style={{ background: "linear-gradient(135deg, var(--sun-soft), var(--surface) 70%)" }}>
      <div className="row" style={{ gap: 8, marginBottom: 10 }}><Lightbulb size={17} color="var(--sun)" /><h3>Amalda qanday ishlaydi</h3></div>
      <p className="muted small" style={{ margin: "0 0 10px" }}>Misol: ishtirokchi hozir 07:00 da turadi, maqsadi 05:30.</p>
      <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
        <li>1-kun budilnik <b>07:00</b>: «Uyg'ondim» — <b>{fromMin(start + v.wake_grace_minutes)}</b> gacha, ovozli raport — <b>{fromMin(start + v.voice_deadline_minutes)}</b> gacha.</li>
        <li>{v.shift_from_day}-kundan budilnik har kuni <b>{v.shift_step_minutes} daqiqa</b> oldinga: {v.shift_from_day}-kun <b>{fromMin(alarm(v.shift_from_day))}</b>, 10-kun <b>{fromMin(alarm(10))}</b>.</li>
        <li>05:30 ga <b>{reachDay ? `${reachDay}-kunda` : "120 kundan keyin"}</b> yetadi.</li>
        <li>{video ? <>{v.video_from_day}-kundan ovoz o'rniga <b>video krujok</b> ({v.video_deadline_minutes} daqiqa ichida), {v.reviewers_per_proof} rotadosh tekshiradi.</> : <>Video so'ralmaydi — har kuni <b>ovozli raport</b>.</>}</li>
        <li><b>{v.max_strikes}</b> ta ogohlantirishda lagerdan chiqariladi{v.sunday_rest ? ", yakshanba — dam olish kuni" : ""}.</li>
      </ul>
    </div>
  );
}

function Field({ f, value, onChange, changed }) {
  let control;
  if (f.type === "bool") control = <Switch on={!!value} onChange={onChange} label={f.label} />;
  else if (f.type === "time") control = <input type="time" className="input" style={{ width: 130 }} value={(value || "").slice(0, 5)} onChange={(e) => onChange(e.target.value)} />;
  else control = <Stepper value={value ?? 0} onChange={onChange} min={f.min ?? 0} max={f.max ?? 999} />;
  return (
    <div className={`setting ${changed ? "changed" : ""}`}>
      <div><b>{f.label}</b>{f.help && <p>{f.help}</p>}</div>
      {control}
    </div>
  );
}

export default function SettingsPage() {
  const { data, error, setData } = useLoad(api.settings);
  const [draft, setDraft] = useState(null);
  useEffect(() => { if (data) setDraft(data.values); }, [data]);
  const [run, busy] = useAction((r) => setData(r));

  const changed = useMemo(() => {
    if (!data || !draft) return [];
    return Object.keys(draft).filter((k) => String(draft[k]).slice(0, 5) !== String(data.values[k]).slice(0, 5));
  }, [data, draft]);

  if (error) return <ErrorBox text={error} />;
  if (!data || !draft) return <Skeleton height={500} />;

  const save = () => run(
    () => api.saveSettings(Object.fromEntries(changed.map((k) => [k, draft[k]]))),
    "Saqlandi. Bot va Mini App 30 soniya ichida yangi qoidalarga o'tadi.",
  );

  return (
    <>
      <PageHead title="Lager qoidalari" sub="Bu yerdagi o'zgarishlar darhol kuchga kiradi — kod yozish shart emas." />
      <div className="grid grid-main" style={{ alignItems: "start" }}>
        <div className="stack">
          {data.groups.map((g) => {
            const Icon = ICONS[g.icon] || Shield;
            return (
              <div key={g.title} className="card">
                <div className="card-head" style={{ justifyContent: "flex-start" }}>
                  <div className="kpi-icon tone-sun" style={{ width: 34, height: 34 }}><Icon size={17} /></div>
                  <h2>{g.title}</h2>
                </div>
                {g.fields.map((f) => (
                  <Field key={f.name} f={f} value={draft[f.name]} changed={changed.includes(f.name)}
                    onChange={(val) => setDraft({ ...draft, [f.name]: val })} />
                ))}
              </div>
            );
          })}
        </div>
        <div className="stack" style={{ position: "sticky", top: 16 }}>
          <Example v={draft} />
        </div>
      </div>
      {changed.length > 0 && (
        <div className="savebar">
          <b>{changed.length} ta o'zgarish saqlanmagan</b>
          <div className="spacer" />
          <button className="btn btn-ghost" style={{ color: "#fff" }} onClick={() => setDraft(data.values)}><RotateCcw size={15} /> Bekor qilish</button>
          <button className="btn btn-primary" disabled={busy} onClick={save}><Save size={15} /> Saqlash</button>
        </div>
      )}
    </>
  );
}
