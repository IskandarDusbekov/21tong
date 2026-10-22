// "Profil" — shaxsiy karta: kim, qaysi rotada, nechanchi o'rinda; statistika, yo'l va sozlamalar.
import { useRef, useState } from "react";
import { Camera, CalendarCheck, Coins, Hourglass, MapPin, Medal, Moon, ShieldCheck, Timer, Trophy, UsersRound, Volume2, XCircle } from "lucide-react";
import { uploadAvatar } from "../api.js";
import { Avatar, ErrorCard, Skeleton, SoundSwitch, ThemeSwitch, useToast } from "../ui.jsx";
import Journey, { stageIcon } from "./Journey.jsx";

function AvatarUpload({ me, onChange }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const p = me.profile || {};
  const onFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      await uploadAvatar(file);
      toast("Profil rasmi yangilandi");
      onChange?.();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="profile-avatar" style={{ position: "relative", cursor: "pointer" }} onClick={() => !busy && input.current?.click()}>
      <input ref={input} type="file" accept="image/*" hidden onChange={onFile} />
      <Avatar name={me.full_name || me.first_name || "?"} size={64} avatar={p.has_avatar ? p.user_id : null} />
      <span className="avatar-edit" aria-label="Rasmni o'zgartirish"><Camera size={13} /></span>
    </div>
  );
}

const STATUS = {
  pending: "Arizangiz ko'rib chiqilmoqda",
  rejected: "Ariza rad etilgan",
  new: "Ariza hali yuborilmagan",
};

function Identity({ me, onChange }) {
  const p = me.profile || {};
  const m = me.membership;
  const j = me.journey;
  const StageIcon = j?.stage ? stageIcon(j.stage) : null;
  const sub = [p.region, p.username && `@${p.username}`].filter(Boolean).join(" · ");
  return (
    <section className="hero profile-hero">
      <div className="profile-id">
        <AvatarUpload me={me} onChange={onChange} />
        <div style={{ minWidth: 0 }}>
          <h2 className="profile-name">{me.full_name || me.first_name}</h2>
          {sub && <div className="profile-sub"><MapPin size={13} /> {sub}</div>}
        </div>
      </div>
      <div className="profile-chips">
        {m ? (
          <>
            {m.squad && <span className="chip"><UsersRound size={13} /> {m.squad}</span>}
            <span className="chip">{m.tribe}</span>
            <span className="chip">{StageIcon && <StageIcon size={13} />}{j?.stage ? j.stage.name : "Yangi boshlovchi"}</span>
          </>
        ) : me.upcoming ? (
          <>
            <span className="chip"><UsersRound size={13} /> {me.upcoming.squad}</span>
            <span className="chip"><Timer size={13} /> Start {me.upcoming.start_date}</span>
          </>
        ) : (
          <span className="chip"><Hourglass size={13} /> {STATUS[me.status] || "Faol oqimda emassiz"}</span>
        )}
      </div>
    </section>
  );
}

function Score({ s }) {
  return (
    <div className="card profile-score">
      <div>
        <Trophy size={18} className="profile-score-icon" />
        <b className="num">{s.points}</b>
        <small>umumiy ball</small>
      </div>
      <div>
        <UsersRound size={18} className="profile-score-icon" />
        <b className="num">{s.squad_rank ?? "—"}<span className="muted">/{s.squad_total}</span></b>
        <small>rotada o'rin</small>
      </div>
      <div>
        <Medal size={18} className="profile-score-icon" />
        <b className="num">{s.tribe_rank ?? "—"}<span className="muted">/{s.tribe_total}</span></b>
        <small>qabilada o'rin</small>
      </div>
    </div>
  );
}

function Stats({ me }) {
  const m = me.membership;
  const items = [
    { icon: Coins, tone: "#c98400", bg: "color-mix(in srgb, #d99b1c 16%, transparent)", value: me.coins, label: "IrodaCoin" },
    { icon: CalendarCheck, tone: "var(--ok)", bg: "var(--ok-soft)", value: me.journey?.survived ?? 0, label: "Kun bajarildi" },
    { icon: ShieldCheck, tone: "var(--rest)", bg: "var(--rest-soft)", value: me.immunities, label: "Immunitet" },
    { icon: XCircle, tone: "var(--bad)", bg: "var(--bad-soft)", value: m ? `${m.strikes}/${me.max_strikes}` : "—", label: "Ogohlantirish" },
  ];
  return (
    <div className="stats stats-4">
      {items.map(({ icon: Icon, tone, bg, value, label }) => (
        <div key={label} className="stat">
          <div className="stat-icon" style={{ background: bg, color: tone }}><Icon size={17} /></div>
          <b className="num">{value}</b>
          <small>{label}</small>
        </div>
      ))}
    </div>
  );
}

function Settings() {
  return (
    <>
      <div className="section-title">Sozlamalar</div>
      <div className="card settings">
        <div className="settings-row settings-col">
          <div className="settings-label"><Moon size={17} /> Rejim</div>
          <ThemeSwitch />
          <small className="muted">«Avto» — Telegram mavzusiga ergashadi.</small>
        </div>
        <div className="settings-row">
          <div className="settings-label"><Volume2 size={17} /> Ovoz belgilari</div>
          <SoundSwitch />
        </div>
      </div>
    </>
  );
}

export default function Profile({ me, error, reload }) {
  if (error && !me) return <ErrorCard text={error} />;
  if (!me) return <div className="stack"><Skeleton height={170} /><Skeleton height={90} /><Skeleton height={240} /></div>;
  const s = me.profile?.standing;
  return (
    <div>
      <Identity me={me} onChange={reload} />
      {s && <Score s={s} />}
      {me.membership && <Stats me={me} />}
      <Journey me={me} error={error} embedded />
      <Settings />
      <p className="muted small" style={{ textAlign: "center", marginTop: 22 }}>21 Tong · intizom lageri</p>
    </div>
  );
}
