import { useState } from "react";
import {
  AlarmClock, Ban, BedDouble, Check, CheckCircle2, Clock, Coins, Hourglass, Lock, Megaphone, Mic,
  Moon, Send, ShieldCheck, Snowflake, Sun, Sunrise, Users, Video, XCircle,
} from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorCard, Sheet, Skeleton, useAction, useLoad } from "../ui.jsx";
import { stageIcon } from "./Journey.jsx";

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

function Link({ icon: Icon, state, title, tag, hint, children }) {
  return (
    <li className={`link ${state}`}>
      <div className="link-icon">{state === "done" ? <Check size={20} strokeWidth={3} /> : <Icon size={20} />}</div>
      <div className="link-body">
        <div className="link-title">{title}{tag}</div>
        {hint && <div className="link-hint">{hint}</div>}
        {children}
      </div>
      <div className="link-state">
        {state === "locked" && <Lock size={16} />}
        {state === "done" && <CheckCircle2 size={18} />}
      </div>
    </li>
  );
}

function Chain({ t, gender, rules }) {
  const isVideo = t.proof_kind === "video";
  const proofState = !t.woke ? "locked"
    : isVideo ? (t.video === "approved" ? "done" : t.video === "rejected" ? "failed" : "active")
    : t.voice ? "done" : "active";
  const proofTag = isVideo && t.video === "reviewing" ? <span className="tag sun"><Hourglass size={11} /> Rota tekshirmoqda</span>
    : isVideo && t.video === "rejected" ? <span className="tag bad">Rad etildi</span>
    : !t.proof_done ? <span className="tag num">{t.proof_deadline} gacha</span>
    : null;

  return (
    <ol className="chain card">
      <Link
        icon={Sun} state={t.woke ? "done" : "active"} title="Uyg'ondim"
        hint={t.woke ? "Birinchi qadam bosildi. Endi buyruqni bajaring." : `Budilnikdan keyin ${rules.grace_minutes} daqiqa ichida — botdagi tugma yoki shu yerda`}
      />
      <Link
        icon={isVideo ? Video : Mic} state={proofState} tag={proofTag}
        title={isVideo ? "Video raport — tashqarida" : "Ovozli raport"}
        hint={
          isVideo
            ? "Tashqariga chiqing, suv iching. Yurib turib gapni o'qigan holda video krujok yozing va botga yuboring. Rotadan 3 kishi tekshiradi."
            : `Gapni ovoz chiqarib o'qing va budilnikdan keyin ${rules.voice_deadline_minutes} daqiqa ichida ovozli xabarni botga yuboring.` + (rules.video_from_day ? ` Video ${rules.video_from_day}-kundan boshlanadi.` : "")
        }
      >
        {isVideo && gender === "F" && (
          <div className="quote" style={{ fontStyle: "normal" }}>
            Yuzingizni ko'rsatish shart emas — orqa kamerani yoqing, ovozingiz eshitilsin.
          </div>
        )}
      </Link>
    </ol>
  );
}

function OrderCard({ t }) {
  return (
    <div className="card order">
      <div className="order-head">
        <Megaphone size={16} /> BUYRUQ №{t.day_number}
      </div>
      <p className="muted small" style={{ margin: "8px 0 6px" }}>Ovoz chiqarib o'qing:</p>
      <div className="order-phrase">«{t.phrase}»</div>
      <div className="order-foot">
        <span><Send size={14} /> Raportni <b>botga</b> yuboring</span>
        <span className="num"><Clock size={14} /> {t.proof_deadline} gacha</span>
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
    return <Empty icon={Clock} title="Anketangiz ko'rib chiqilmoqda" text="Admin tasdiqlagach, botda /join orqali oqimga qo'shilasiz." />;
  }
  return <Empty icon={Sunrise} title="Siz hozir faol oqimda emassiz" text="Botda /join buyrug'i orqali yangi oqimga qo'shiling." />;
}

export default function Today({ me, error, reload }) {
  const [askFreeze, setAskFreeze] = useState(false);
  const [run, busy] = useAction(reload);

  if (error && !me) return <ErrorCard text={error} />;
  if (!me) return <div className="stack"><Skeleton height={190} /><Skeleton height={86} /><Skeleton height={230} /></div>;
  if (!me.membership || !me.journey) return <NoMembership status={me.status} />;

  const t = me.today;
  const banner = t && DAY_BANNERS[t.status];
  const isSunday = me.journey.days.find((d) => d.today)?.weekday === 6;

  return (
    <div>
      <Hero me={me} />
      <Stats me={me} />

      <div className="section-title">Bugungi zanjir</div>
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
          {t.woke && !t.proof_done && t.phrase && <OrderCard t={t} />}
          <Chain t={t} gender={me.gender} rules={me.journey.rules} />
          {!t.woke && (
            <button className="btn btn-primary btn-xl btn-block" disabled={busy} onClick={() => run(api.wake, "Xayrli tong! Buyruqni bajaring.")}>
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
    </div>
  );
}
