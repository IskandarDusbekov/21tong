import { useState } from "react";
import { Check, Play, Quote, Video, X } from "lucide-react";
import { api } from "../api.js";
import { go } from "../router.js";
import { Empty, ErrorBox, PageHead, Person, Pill, Seg, Skeleton, fmtAgo, useAction, useLoad } from "../ui.jsx";

function Votes({ votes }) {
  return (
    <div className="row" style={{ gap: 4 }} title="Rotadoshlar ovozi">
      {votes.map((v, i) => (
        <span key={i} className={`pill tone-${v === true ? "ok" : v === false ? "bad" : "mute"}`} style={{ padding: "2px 6px" }}>
          {v === true ? <Check size={12} /> : v === false ? <X size={12} /> : "…"}
        </span>
      ))}
    </div>
  );
}

export default function Videos({ onChange }) {
  const [status, setStatus] = useState("reviewing");
  const [playing, setPlaying] = useState(null);
  const { data, error, reload } = useLoad(() => api.videos(status), [status]);
  const [run, busy] = useAction(async () => { await reload(); onChange?.(); });

  return (
    <>
      <PageHead title="Video raportlar" sub="Video yoqilgan kunlarda rotadoshlar tekshiradi. Kerak bo'lsa bu yerda qo'lda hal qiling.">
        <Seg value={status} onChange={setStatus} options={[
          { value: "reviewing", label: "Tekshirilmoqda" }, { value: "approved", label: "Tasdiqlangan" },
          { value: "rejected", label: "Rad etilgan" }, { value: "all", label: "Hammasi" },
        ]} />
      </PageHead>
      {error && <ErrorBox text={error} />}
      {!data && !error && <Skeleton height={200} />}
      {data && !data.length && (
        <div className="card"><Empty icon={Video} title="Video yo'q" text="Video raport Lager qoidalarida yoqiladi (masalan 7-kundan)." /></div>
      )}
      <div className="stack">
        {data?.map((v) => (
          <div key={v.id} className="card card-pad">
            <div className="row" style={{ flexWrap: "wrap", gap: 14 }}>
              <div style={{ cursor: "pointer" }} onClick={() => go("members", { open: v.membership_id })}>
                <Person user={v.user} sub={`${v.squad || "—"} · ${v.day}-kun · ${fmtAgo(v.uploaded_at)}`} />
              </div>
              <div className="spacer" />
              <Votes votes={v.votes} />
              {v.has_video && (
                <button className="btn btn-outline btn-sm" onClick={() => setPlaying(playing === v.id ? null : v.id)}>
                  <Play size={15} /> {playing === v.id ? "Yopish" : "Ko'rish"}
                </button>
              )}
              {v.status === "reviewing" ? (
                <>
                  <button className="btn btn-ok btn-sm" disabled={busy} onClick={() => run(() => api.videoDecide(v.id, "approve"))}><Check size={15} /> Tasdiqlash</button>
                  <button className="btn btn-bad btn-sm" disabled={busy} onClick={() => run(() => api.videoDecide(v.id, "reject"))}><X size={15} /> Rad etish</button>
                </>
              ) : (
                <Pill tone={v.status === "approved" ? "ok" : "bad"} dot>{v.status_label}</Pill>
              )}
            </div>
            {playing === v.id && v.has_video && (
              <video className="panel-video" src={api.videoUrl(v.id)} controls autoPlay playsInline />
            )}
            {v.phrase && (
              <div className="row small" style={{ gap: 8, marginTop: 12, padding: "8px 12px", background: "var(--surface-2)", borderRadius: 10 }}>
                <Quote size={14} color="var(--sun)" /> O'qilishi kerak edi: <i>«{v.phrase}»</i>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
