import { useRef, useState } from "react";
import {
  AlarmClock, Ban, BedDouble, Camera, Check, CheckCircle2, Clock, Coins, Footprints, GlassWater, Hourglass,
  Lock, Megaphone, MessagesSquare, Mic, Moon, ShieldCheck, Snowflake, Sun, Sunrise, Timer, Users, Video, XCircle,
} from "lucide-react";
import { api, uploadWater } from "../api.js";
import { Avatar, Empty, ErrorCard, haptic, Sheet, Skeleton, useAction, useLoad, useToast } from "../ui.jsx";
import { sound } from "../sound.js";
import { stageIcon } from "./Journey.jsx";
import VideoRecorder from "./VideoRecorder.jsx";

/** "Uyg'ondim" marosimi — quyosh portlashi, bir lahzaga to'liq ekran. */
function WakeRitual() {
  return (
    <div className="ritual" role="status" aria-label="Xayrli tong">
      <div className="ritual-sun">
        <Sunrise size={64} />
        <span className="ritual-rays" />
      </div>
      <b className="ritual-text">Xayrli tong, jangchi!</b>
      <small>Bugun kechagidan kuchliroqsan</small>
    </div>
  );
}

function DayRing({ day, total }) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const pct = Math.min(day / total, 1);
  return (
    <div className="ring" aria-label={`${day}-kun, jami ${total}`}>
      <svg width="96" height="96" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r={r} fill="none" stroke="rgb(255 255 255 / 16%)" strokeWidth="7" />
        <circle
          cx="48" cy="48" r={r} fill="none" stroke="url(#ring-grad)" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} style={{ transition: "stroke-dashoffset .8s" }}
        />
        <defs>
          <linearGradient id="ring-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#ffd36b" />
            <stop offset="1" stopColor="#ff7a2f" />
          </linearGradient>
        </defs>
      </svg>
      <div className="ring-label">
        <b className="num">{day}</b>
        <span>/ {total} kun</span>
      </div>
    </div>
  );
}

function Hero({ me }) {
  const { membership: m, today: t, journey: j } = me;
  const StageIcon = j.stage ? stageIcon(j.stage) : Sunrise;
  return (
    <section className="hero">
      <div className="hero-top">
        <span>{m.squad ? <><b>{m.squad}</b> · </> : null}{m.tribe}</span>
        <span className="chip"><StageIcon size={14} />{j.stage ? j.stage.name : "Yangi boshlovchi"}</span>
      </div>
      <div className="hero-main">
        <DayRing day={j.current_day || j.duration} total={j.duration} />
        <div>
          <div className="hero-alarm-label"><AlarmClock size={15} />Bugungi budilnik</div>
          <div className="hero-alarm num">{t ? t.alarm_time : "—"}</div>
          <div className="hero-sub">
            {j.tomorrow_alarm ? <>Ertaga <b className="num">{j.tomorrow_alarm}</b> · maqsad {m.target_wake_time}</> : "Oqimning oxirgi kuni"}
          </div>
        </div>
      </div>
    </section>
  );
}

function Stats({ me }) {
  const strikes = me.membership.strikes;
  return (
    <div className="stats">
      <div className="stat">
        <div className="stat-icon" style={{ background: "var(--bad-soft)", color: "var(--bad)" }}><XCircle size={17} /></div>
        <div className="strike-dots" aria-label={`${strikes} ta ogohlantirish`}>
          {Array.from({ length: me.max_strikes }, (_, i) => <i key={i} className={i < strikes ? "on" : ""} />)}
        </div>
        <small>Ogohlantirish</small>
      </div>
      <div className="stat">
        <div className="stat-icon" style={{ background: "var(--rest-soft)", color: "var(--rest)" }}><ShieldCheck size={17} /></div>
        <b className="num">{me.immunities}</b>
        <small>Immunitet</small>
      </div>
      <div className="stat">
        <div className="stat-icon" style={{ background: "color-mix(in srgb, #d99b1c 16%, transparent)", color: "#c98400" }}><Coins size={17} /></div>
        <b className="num">{me.coins}</b>
        <small>IrodaCoin</small>
      </div>
    </div>
  );
}

export function Windows({ windows }) {
  const items = [
    { key: "morning", title: "Tonggi oyna", icon: Sunrise },
    { key: "evening", title: "Kechki oyna", icon: Moon },
  ];
  return (
    <div className="windows">
      {items.map(({ key, title, icon: Icon }) => {
        const w = windows[key];
        return (
          <div key={key} className={`window ${w.open ? "open" : ""}`}>
            <div className="window-icon"><Icon size={18} /></div>
            <div>
              <b>{title}</b>
              <small className="muted num" style={{ display: "block", whiteSpace: "nowrap" }}>{w.start}–{w.end}</small>
              <small className="muted"><span className="dot" />{w.open ? "Ochiq" : "Yopiq"}</small>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CoinChip({ amount, earned }) {
  if (!amount) return null;
  return (
    <span className={`coin-chip ${earned ? "earned" : ""}`} title={earned ? "Tanga olindi" : "Bajarsangiz — tanga"}>
      {earned ? <Check size={12} strokeWidth={3} /> : <Coins size={12} />}
      <span className="num">{earned ? amount : `+${amount}`}</span>
    </span>
  );
}

function Task({ n, icon: Icon, state, title, tag, hint, coins, earned, children }) {
  return (
    <li className={`task ${state}`}>
      <div className="task-badge">
        {state === "done" ? <Check size={18} strokeWidth={3} /> : state === "locked" ? <Lock size={15} /> : <Icon size={19} />}
      </div>
      <div className="task-body">
        <div className="task-title"><span className="task-n num">{n}</span>{title}</div>
        {tag && <div className="task-tags">{tag}</div>}
        {hint && <div className="task-hint">{hint}</div>}
        {children}
      </div>
      <CoinChip amount={coins} earned={earned} />
    </li>
  );
}

/** Kunlik 3 topshiriq: ① uyg'onish + ovozli raport, ② iliq suv (rasm), ③ ko'chada yurish (video). */
function Tasks({ t, gender, rules, onRecord, onWater, waterBusy }) {
  const c = t.coins || {};
  const voiceOk = t.voice && !t.voice_late;

  const s1 = !t.woke ? "active" : voiceOk ? "done" : t.voice ? "failed" : "active";
  const hint1 = !t.woke
    ? `Budilnikdan keyin ${rules.grace_minutes} daqiqa ichida «Uyg'ondim» tugmasini bosing.`
    : voiceOk ? "Ovozli raport qabul qilindi."
    : t.voice ? "Ovozli raport kech keldi — tanga berilmadi."
    : "Yuqoridagi gapni ovoz chiqarib o'qing va ovozli xabar qilib botga yuboring.";
  const tag1 = t.woke && !t.voice ? <span className="tag num"><Clock size={11} /> {t.voice_deadline} gacha</span> : null;

  const s2 = !t.woke ? "locked" : t.water ? "done" : "active";
  const hint2 = !t.woke ? "Uyg'ongach ochiladi."
    : t.water ? "Rasm yuborildi — organizm uyg'ondi!"
    : "Bir stakan iliq suv iching va stakanni rasmga oling. Rotangiz ko'radi.";

  const s3 = !t.woke ? "locked"
    : t.video === "approved" ? "done"
    : t.video === "rejected" ? "failed"
    : t.video === "reviewing" ? "review" : "active";
  const tag3 = t.video === "reviewing" ? <span className="tag sun"><Hourglass size={11} /> Rota tekshirmoqda</span>
    : t.video === "rejected" ? <span className="tag bad">Rota rad etdi</span>
    : t.woke && !t.video && t.video_required ? <span className="tag bad num">Majburiy · {t.video_deadline} gacha</span>
    : null;
  const hint3 = !t.woke ? "Uyg'ongach ochiladi."
    : t.video === "approved" ? "Video tasdiqlandi. Zo'r yurish!"
    : t.video === "reviewing" ? "Video rotaga yuborildi — tasdiqlangach tanga beriladi."
    : t.video === "rejected" ? "Rotadoshlar videoni qabul qilmadi."
    : "Tashqariga chiqing, yurib turib gapni o'qing va 10 soniyalik video yozing. Rotadan 3 kishi tekshiradi.";

  const states = [s1, s2, s3];
  const done = states.filter((s) => s === "done").length;
  const all = Object.values(c);
  const earnedSum = all.filter((x) => x.earned).reduce((a, x) => a + x.amount, 0);
  const totalSum = all.reduce((a, x) => a + x.amount, 0);

  return (
    <div className="card tasks">
      <div className="tasks-head">
        <div>
          <b>Bugungi topshiriqlar</b>
          <small className="muted">{done === 3 ? "Hammasi bajarildi — zo'r!" : `${done}/3 bajarildi`}</small>
        </div>
        {totalSum > 0 && (
          <span className="tasks-coins"><Coins size={15} /><b className="num">{earnedSum}</b><span className="muted num">/{totalSum}</span></span>
        )}
      </div>
      <div className="progress"><i style={{ width: `${Math.max((done / 3) * 100, 3)}%` }} /></div>
      <ol className="task-list">
        <Task
          n={1} icon={Mic} state={s1} title="Uyg'onish va ovozli raport" tag={tag1} hint={hint1}
          coins={(c.wake?.amount || 0) + (c.voice?.amount || 0)} earned={c.wake?.earned && c.voice?.earned}
        />
        <Task n={2} icon={GlassWater} state={s2} title="Iliq suv ichish" hint={hint2} coins={c.water?.amount} earned={c.water?.earned}>
          {s2 === "active" && (
            <button className="btn btn-primary btn-sm task-btn" disabled={waterBusy} onClick={onWater}>
              <Camera size={16} /> {waterBusy ? "Yuborilmoqda…" : "Rasmga olish"}
            </button>
          )}
        </Task>
        <Task n={3} icon={Footprints} state={s3} title="Ko'chada yurish" tag={tag3} hint={hint3} coins={c.video?.amount} earned={c.video?.earned}>
          {s3 === "active" && gender === "F" && (
            <div className="quote" style={{ fontStyle: "normal" }}>
              Yuzingizni ko'rsatish shart emas — orqa kamerani yoqing, ovozingiz eshitilsin.
            </div>
          )}
          {s3 === "active" && (
            <button className="btn btn-primary btn-sm task-btn" onClick={onRecord}>
              <Video size={16} /> Video yozish
            </button>
          )}
        </Task>
      </ol>
    </div>
  );
}

function OrderCard({ t }) {
  return (
    <div className="card order">
      <div className="order-head">
        <Megaphone size={16} /> BUYRUQ №{t.day_number}
      </div>
      <p className="muted small" style={{ margin: "8px 0 6px" }}>Ovoz chiqarib o'qing — ovozli raportda ham, videoda ham:</p>
      <div className="order-phrase">«{t.phrase}»</div>
      <div className="order-foot">
        <span><Mic size={14} /> Ovoz — <b>botga</b></span>
        <span><Video size={14} /> Video — <b>shu yerda</b></span>
      </div>
    </div>
  );
}

const ROLL = {
  done: { icon: CheckCircle2, color: "var(--ok)", label: "Safda" },
  woke: { icon: Hourglass, color: "var(--sun)", label: "Turdi, raport yo'q" },
  absent: { icon: XCircle, color: "var(--bad)", label: "Javob yo'q" },
  frozen: { icon: Snowflake, color: "var(--ice)", label: "Muzlatilgan" },
  rest: { icon: BedDouble, color: "var(--rest)", label: "Yakshanba" },
  out: { icon: Ban, color: "var(--muted)", label: "Chiqarilgan" },
};

function SquadRoll() {
  const { data } = useLoad(api.squad);
  if (!data) return null;
  const pct = data.total ? (data.done / data.total) * 100 : 0;
  return (
    <>
      <div className="section-title">{data.squad} · bugungi raport</div>
      <div className="card">
        <div className="row-between">
          <span className="muted small"><Users size={14} style={{ verticalAlign: -2 }} /> Safda</span>
          <b className="num">{data.done}/{data.total}</b>
        </div>
        <div className="progress"><i style={{ width: `${Math.max(pct, 2)}%`, background: "linear-gradient(90deg, #4fd28f, var(--ok))" }} /></div>
        <ul className="roll">
          {data.members.map((m, i) => {
            const s = ROLL[m.status];
            return (
              <li key={i} className={m.status === "out" ? "out" : ""}>
                <Avatar name={m.name} />
                <span className="name">{m.name}{m.me && <span className="tag" style={{ marginLeft: 6 }}>siz</span>}</span>
                {m.strikes > 0 && m.status !== "out" && (
                  <span className="strikes" title={`${m.strikes} ta ogohlantirish`}>
                    {Array.from({ length: m.strikes }, (_, k) => <i key={k} />)}
                  </span>
                )}
                <s.icon size={18} color={s.color} aria-label={s.label} />
              </li>
            );
          })}
        </ul>
      </div>
    </>
  );
}

const DAY_BANNERS = {
  completed: { tone: "ok", icon: CheckCircle2, title: "Bugungi kun bajarildi", text: "Sen zo'r ketyapsan. Ertaga ham shunday!" },
  frozen: { tone: "ice", icon: Snowflake, title: "Bugun muzlatilgan kun", text: "Dam oling va tezroq tuzaling. Ogohlantirish berilmaydi." },
  rest: { tone: "rest", icon: BedDouble, title: "Yakshanba — dam olish", text: "Ogohlantirish yo'q. Barvaqt turganlar Immunitet oladi." },
  failed: { tone: "bad", icon: XCircle, title: "Bugun bajarilmadi", text: "Sen o'zgaraman deb kelganding. Ertaga isbotla." },
};

function NoMembership({ status }) {
  if (status === "pending") {
    return <Empty icon={Clock} title="Arizangiz ko'rib chiqilmoqda" text="Tasdiqlangach, rotangiz va start sanasi shu yerda chiqadi." />;
  }
  return <Empty icon={Sunrise} title="Siz hozir faol oqimda emassiz" text="Botda /join buyrug'i orqali yangi oqimdagi rotani tanlang." />;
}

const GUIDE = [
  { icon: AlarmClock, title: "Bot uyg'otadi", text: (u) => `Budilnik ${u.alarm} da «TURISH!» xabari keladi. Ostidagi «Uyg'ondim» tugmasini ${u.rules.wake_grace} daqiqa ichida bosing.` },
  { icon: Mic, title: "1-topshiriq: ovozli raport", text: (u) => `Bot bergan gapni ${u.rules.voice_deadline} daqiqa ichida ovozli xabar qilib botga yuboring: 🎙 tugmasini bosib turing, o'qing, qo'yib yuboring.` },
  { icon: GlassWater, title: "2-topshiriq: iliq suv", text: () => "Bir stakan iliq suv iching va «Bugun» bo'limida stakanni rasmga oling." },
  { icon: Footprints, title: "3-topshiriq: ko'chada yurish", text: () => "Tashqariga chiqing, yurib turib gapni o'qing va «Bugun» bo'limida 10 soniyalik video yozing." },
  { icon: Coins, title: "Har topshiriq — tanga", text: () => "Bajargan har bir topshiriq uchun IrodaCoin olasiz va reytingda yuqoriga chiqasiz." },
];

/** Qabul qilingan, lekin oqim hali boshlanmagan: sanoq, rota, yo'riqnoma. */
function Upcoming({ u, me }) {
  const left = u.days_left;
  const starts = left <= 0 ? "Bugun boshlanadi!" : left === 1 ? "Ertaga boshlanadi!" : null;
  return (
    <div>
      <section className="hero countdown-hero">
        <div className="hero-top">
          <span><b>{u.squad}</b> · {u.tribe}</span>
          <span className="chip"><Timer size={14} />Start {u.start_date}</span>
        </div>
        <div className="countdown">
          <span className="countdown-label">Lager boshlanishiga</span>
          {starts ? (
            <b className="countdown-now">{starts}</b>
          ) : (
            <div className="countdown-main">
              <b className="num countdown-num">{left}</b>
              <span className="countdown-unit">kun<br />qoldi</span>
            </div>
          )}
        </div>
        <div className="countdown-foot">
          <span><AlarmClock size={14} /> Birinchi budilnik <b className="num">{u.alarm}</b></span>
          <span>Maqsad <b className="num">{u.target}</b></span>
        </div>
      </section>
      <div className="banner ok" style={{ marginTop: 12 }}>
        <div className="banner-icon"><MessagesSquare size={22} /></div>
        <div><b>Rotangiz bilan tanishing</b><small className="muted">«Rota» bo'limida chat ochiq — start'gacha suhbatlashib oling.</small></div>
      </div>
      <div className="section-title">Har tong nima qilasiz</div>
      <ol className="chain card">
        {GUIDE.map((g, i) => (
          <li key={i} className="link active">
            <div className="link-icon"><g.icon size={20} /></div>
            <div className="link-body"><div className="link-title">{i + 1}. {g.title}</div><div className="link-hint">{g.text(u)}</div></div>
          </li>
        ))}
      </ol>
      <div className="banner rest" style={{ marginTop: 12 }}>
        <div className="banner-icon"><Mic size={22} /></div>
        <div><b>Hozir mashq qiling</b><small className="muted">Botga istalgan ovozli xabar yuboring — bot «Mashq qabul qilindi» deydi.</small></div>
      </div>
      <div className="banner ok" style={{ marginTop: 10 }}>
        <div className="banner-icon"><Users size={22} /></div>
        <div><b>Yolg'iz bo'lma</b><small className="muted">Do'stingizni ham chaqiring — birga erta turish osonroq.</small></div>
      </div>
      {me.awards?.length > 0 && <div className="section-title">Mukofotlaringiz «Profil» bo'limida</div>}
    </div>
  );
}

export default function Today({ me, error, reload }) {
  const [askFreeze, setAskFreeze] = useState(false);
  const [ritual, setRitual] = useState(false);
  const [recording, setRecording] = useState(false);
  const [waterBusy, setWaterBusy] = useState(false);
  const waterInput = useRef(null);
  const toast = useToast();
  const [run, busy] = useAction(reload);

  const onWaterFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setWaterBusy(true);
    try {
      await uploadWater(file);
      sound.success();
      toast("Iliq suv qabul qilindi — tanga berildi!");
      reload();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setWaterBusy(false);
    }
  };

  const doWake = () => {
    setRitual(true);
    haptic("success");
    sound.wake();
    run(api.wake);
    setTimeout(() => setRitual(false), 1900);
  };

  if (error && !me) return <ErrorCard text={error} />;
  if (!me) return <div className="stack"><Skeleton height={190} /><Skeleton height={86} /><Skeleton height={230} /></div>;
  if (me.upcoming) return <Upcoming u={me.upcoming} me={me} />;
  if (!me.membership || !me.journey) return <NoMembership status={me.status} />;

  const t = me.today;
  const banner = t && DAY_BANNERS[t.status];
  const isSunday = me.journey.days.find((d) => d.today)?.weekday === 6;

  return (
    <div>
      {ritual && <WakeRitual />}
      <Hero me={me} />
      <Stats me={me} />

      <input ref={waterInput} type="file" accept="image/*" capture="environment" hidden onChange={onWaterFile} />
      <div className="section-title">Bugun</div>
      {banner ? (
        <div className={`banner ${banner.tone}`}>
          <div className="banner-icon"><banner.icon size={22} /></div>
          <div><b>{banner.title}</b><small className="muted">{banner.text}</small></div>
        </div>
      ) : t ? (
        <div className="stack">
          {isSunday && (
            <div className="banner rest">
              <div className="banner-icon"><BedDouble size={22} /></div>
              <div><b>Yakshanba</b><small className="muted">Uxlash mumkin. Lekin hammasini bajarsangiz — 1 ta Immunitet.</small></div>
            </div>
          )}
          {t.woke && t.phrase && (!t.voice || !t.video) && <OrderCard t={t} />}
          <Tasks
            t={t} gender={me.gender} rules={me.journey.rules}
            onRecord={() => setRecording(true)} onWater={() => waterInput.current?.click()} waterBusy={waterBusy}
          />
          {!t.woke && (
            <button className="btn btn-primary btn-xl btn-block wake-btn" disabled={busy} onClick={doWake}>
              <Sun size={22} /> Uyg'ondim
            </button>
          )}
        </div>
      ) : (
        <Empty icon={Sunrise} title="Bugun oqim kuni emas" />
      )}

      <SquadRoll key={t?.status + String(t?.woke)} />

      <div className="section-title">Chat oynalari</div>
      <Windows windows={me.journey.windows} />

      {me.membership.freezes_left > 0 && (
        <button className="btn btn-ghost btn-block" style={{ marginTop: 18 }} onClick={() => setAskFreeze(true)}>
          <Snowflake size={17} /> Ertangi kunni muzlatish
        </button>
      )}
      {askFreeze && (
        <Sheet
          icon={Snowflake} tone="var(--ice)" title="Ertangi kunni muzlatasizmi?"
          text={`Kasal bo'lsangiz — ertangi kun uchun ogohlantirish berilmaydi. Qolgan imkoniyat: ${me.membership.freezes_left} ta, faqat kechqurun ishlaydi.`}
          confirm="Muzlatish"
          onConfirm={() => run(() => api.freeze(""), "Ertangi kun muzlatildi. Tuzalib keting!")}
          onClose={() => setAskFreeze(false)}
        />
      )}
      {recording && (
        <VideoRecorder onClose={() => setRecording(false)} onDone={() => { setRecording(false); reload(); }} />
      )}
    </div>
  );
}
