import { useEffect, useMemo, useRef, useState } from "react";
import { MessageSquareText, Search, SendHorizontal, Star, Trash2, UsersRound } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorBox, PageHead, Pill, Seg, Skeleton, fmtAgo, useAction, useConfirm, useLoad } from "../ui.jsx";

const fmtTime = (v) => new Date(v).toLocaleTimeString("uz", { hour: "2-digit", minute: "2-digit" });
const GENDER = { M: { label: "Yigitlar", tone: "info" }, F: { label: "Qizlar", tone: "sun" } };

/** Guruh "belgisi" — rota raqami, jinsga qarab rang. */
function SquadMark({ s, size = 40 }) {
  return <span className={`squad-mark g-${s.gender}`} style={{ width: size, height: size }}>{s.number}</span>;
}

function GroupItem({ s, on, onClick }) {
  return (
    <button className={`group-item ${on ? "on" : ""}`} onClick={onClick}>
      <SquadMark s={s} />
      <div className="group-item-body">
        <div className="row-between" style={{ gap: 8 }}>
          <b>{s.squad}</b>
          {s.last && <small className="muted">{fmtTime(s.last.at)}</small>}
        </div>
        <div className="group-item-sub">
          {s.last ? <><b>{s.last.mentor ? "Siz" : s.last.author}:</b> {s.last.text}</> : `${s.wake} · ${s.members.length} kishi`}
        </div>
      </div>
      {s.count > 0 && <span className="group-count">{s.count}</span>}
    </button>
  );
}

/** Bitta guruh — bugungi xabarlar, mentor sifatida yozish va yomon xabarni o'chirish. */
function Thread({ s, onChanged }) {
  const confirm = useConfirm();
  const { data, error, reload } = useLoad(() => api.squadChat(s.id), [s.id]);
  const [text, setText] = useState("");
  const listRef = useRef(null);
  const [run] = useAction(async () => { await reload(); onChanged?.(); });
  const [send, sending] = useAction(async () => { setText(""); await reload(); onChanged?.(); });

  // Har 15 soniyada yangilanadi — rotada nima yozilayotgani jonli ko'rinsin
  useEffect(() => {
    const t = setInterval(reload, 15000);
    return () => clearInterval(t);
  }, [reload]);
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [data?.messages.length]);

  const submit = () => text.trim() && !sending && send(() => api.sendMentorMessage(s.id, text.trim()));
  const remove = async (m) => {
    if (await confirm({ title: "Xabarni o'chirasizmi?", text: `«${m.text}»`, confirm: "O'chirish", danger: true }))
      run(() => api.deleteChatMessage(m.id), "O'chirildi.");
  };

  return (
    <div className="card thread">
      <div className="thread-head">
        <SquadMark s={s} size={44} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <h2>{s.squad}</h2>
          <p className="muted small" style={{ margin: 0 }}>{s.tribe} · {s.cohort}</p>
        </div>
        <Pill tone="sun"><Star size={12} /> Siz — mentor</Pill>
      </div>
      <div className="thread-members">
        <span className="mentor-chip"><Star size={11} /> Mentor</span>
        {s.members.map((n, i) => <span key={i} className="member-chip"><Avatar name={n} size={20} />{n}</span>)}
        {!s.members.length && <span className="muted small">Hali a'zo yo'q</span>}
      </div>
      <div className="thread-body" ref={listRef}>
        {error && <ErrorBox text={error} />}
        {!data && !error && <Skeleton height={160} />}
        {data && !data.messages.length && (
          <Empty icon={MessageSquareText} title="Bugun xabar yo'q" text="Mentor sifatida birinchi bo'lib yozing — rota a'zolari ilovada ko'radi." />
        )}
        {data?.messages.map((m) => (
          <div key={m.id} className={`pmsg ${m.mentor ? "mentor" : ""}`}>
            {!m.mentor && <Avatar name={m.author} size={30} />}
            <div className="pmsg-body">
              {!m.mentor && <b className="pmsg-author">{m.author}</b>}
              <div>{m.text}</div>
              <small title={fmtAgo(m.at)}>{m.mentor && "Mentor · "}{fmtTime(m.at)}</small>
            </div>
            <button className="btn btn-ghost btn-icon pmsg-del" onClick={() => remove(m)} aria-label="Xabarni o'chirish"><Trash2 size={14} /></button>
          </div>
        ))}
      </div>
      <form className="composer" onSubmit={(e) => { e.preventDefault(); submit(); }}>
        <textarea
          className="input" rows={1} value={text} maxLength={1000} placeholder={`${s.squad}ga mentor sifatida yozing…`}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
        />
        <button className="btn btn-primary" disabled={!text.trim() || sending} aria-label="Yuborish"><SendHorizontal size={16} /></button>
      </form>
    </div>
  );
}

export default function Chats() {
  const { data, error, reload } = useLoad(api.chats);
  const [openId, setOpenId] = useState(null);
  const [gender, setGender] = useState("");
  const [q, setQ] = useState("");

  const items = useMemo(() => (data || []).filter((s) =>
    (!gender || s.gender === gender) &&
    (!q || `${s.squad} ${s.tribe} ${s.members.join(" ")}`.toLowerCase().includes(q.toLowerCase()))
  ), [data, gender, q]);
  // Oqim → qabila bo'yicha guruhlash
  const groups = useMemo(() => {
    const out = new Map();
    for (const s of items) {
      const key = `${s.cohort} · ${s.tribe}`;
      if (!out.has(key)) out.set(key, []);
      out.get(key).push(s);
    }
    return [...out.entries()];
  }, [items]);
  const open = data?.find((s) => s.id === openId) || items[0];
  const people = data?.reduce((a, s) => a + s.members.length, 0) || 0;
  const count = (g) => data?.filter((s) => !g || s.gender === g).length;

  return (
    <>
      <PageHead
        title="Guruhlar"
        sub={data ? `${data.length} ta rota · ${people} kishi · har bir guruhda siz mentorsiz va istalgan vaqtda yoza olasiz` : "…"}
      >
        <Seg value={gender} onChange={setGender} options={[
          { value: "", label: "Hammasi", count: count("") },
          { value: "M", label: "Yigitlar", count: count("M") },
          { value: "F", label: "Qizlar", count: count("F") },
        ]} />
      </PageHead>
      {error && <ErrorBox text={error} />}
      {!data && !error && <Skeleton height={420} />}
      {data && !data.length && (
        <div className="card"><Empty icon={UsersRound} title="Guruh yo'q" text="Arizalar qabul qilinganda rotalar o'zi ochiladi." /></div>
      )}
      {data && data.length > 0 && (
        <div className="groups-layout">
          <div className="card group-list">
            <div className="search" style={{ padding: 12 }}>
              <Search size={15} style={{ left: 23 }} />
              <input className="input" placeholder="Rota yoki ism…" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            {groups.map(([title, list]) => (
              <div key={title}>
                <div className="msg-group row-between">
                  <span>{title}</span>
                  <Pill tone={GENDER[list[0].gender]?.tone || "mute"}>{list.length}</Pill>
                </div>
                {list.map((s) => <GroupItem key={s.id} s={s} on={open?.id === s.id} onClick={() => setOpenId(s.id)} />)}
              </div>
            ))}
            {!items.length && <div className="muted small" style={{ padding: 16 }}>Hech narsa topilmadi.</div>}
          </div>
          {open && <Thread key={open.id} s={open} onChanged={reload} />}
        </div>
      )}
    </>
  );
}
