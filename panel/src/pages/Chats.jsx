import { useState } from "react";
import { MessageSquareText, Trash2, UsersRound } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorBox, PageHead, Pill, Skeleton, fmtAgo, useAction, useConfirm, useLoad } from "../ui.jsx";

/** Bitta rota chati — bugungi xabarlar; yomon xabarni o'chirish mumkin. */
function Thread({ squadId, onChanged }) {
  const confirm = useConfirm();
  const { data, error, reload } = useLoad(() => api.squadChat(squadId), [squadId]);
  const [run] = useAction(async () => { await reload(); onChanged?.(); });
  const remove = async (m) => {
    if (await confirm({ title: "Xabarni o'chirasizmi?", text: `«${m.text}»`, confirm: "O'chirish", danger: true }))
      run(() => api.deleteChatMessage(m.id), "O'chirildi.");
  };
  if (error) return <ErrorBox text={error} />;
  if (!data) return <Skeleton height={160} />;
  if (!data.messages.length) return <Empty icon={MessageSquareText} title="Bugun xabar yo'q" text="Bu rotada bugun hali yozishmagan." />;
  return (
    <div className="chat-mod">
      {data.messages.map((m) => (
        <div key={m.id} className="chat-mod-row">
          <Avatar name={m.author} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="small"><b>{m.author}</b> <span className="muted">· {fmtAgo(m.at)}</span></div>
            <div style={{ overflowWrap: "anywhere" }}>{m.text}</div>
          </div>
          <button className="btn btn-ghost btn-icon" onClick={() => remove(m)} aria-label="Xabarni o'chirish"><Trash2 size={14} /></button>
        </div>
      ))}
    </div>
  );
}

export default function Chats() {
  const { data, error, reload } = useLoad(api.chats);
  const [open, setOpen] = useState(null);
  return (
    <>
      <PageHead title="Rota chatlari" sub="Rotalarda bugun nima yozilmoqda — yomon so'z yoki kelishmovchilikni shu yerdan ko'ring va kerak bo'lsa o'chiring." />
      {error && <ErrorBox text={error} />}
      {!data && !error && <Skeleton height={200} />}
      {data && !data.length && (
        <div className="card"><Empty icon={UsersRound} title="Chat yo'q" text="Davom etayotgan oqimdagi rotalar shu yerda chiqadi." /></div>
      )}
      <div className="stack">
        {data?.map((s) => (
          <div key={s.id} className="card card-pad">
            <div className="row-between" style={{ cursor: "pointer", gap: 12 }} onClick={() => setOpen(open === s.id ? null : s.id)}>
              <div style={{ minWidth: 0 }}>
                <div><b>{s.squad}</b> <span className="muted small">· {s.tribe}</span></div>
                {s.last ? (
                  <div className="muted small" style={{ marginTop: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 420 }}>
                    <b>{s.last.author}:</b> {s.last.text}
                  </div>
                ) : <div className="muted small" style={{ marginTop: 2 }}>Bugun xabar yo'q</div>}
              </div>
              <Pill tone={s.count ? "sun" : "mute"}>{s.count} xabar</Pill>
            </div>
            {open === s.id && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line)" }}>
                <Thread squadId={s.id} onChanged={reload} />
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
