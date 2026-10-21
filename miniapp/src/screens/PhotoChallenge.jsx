// Tonggi rasm chelenji: 2 tagacha rasm yuklash, qabiladoshlar rasmiga 🔥, eng yaxshilari yuqoriga chiqadi.
import { useEffect, useRef, useState } from "react";
import { Camera, Crown, Flame, ImagePlus, Medal } from "lucide-react";
import { api, photoImage, uploadPhoto } from "../api.js";
import { Avatar, Empty, Skeleton, useAction, useLoad } from "../ui.jsx";
import { sound } from "../sound.js";

const RANK_BADGE = { 1: { icon: Crown, color: "#f2b705" }, 2: { icon: Medal, color: "#b8c0cc" }, 3: { icon: Medal, color: "#cd7f32" } };

function Thumb({ id }) {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    let url;
    photoImage(id).then((u) => { url = u; setSrc(u); }).catch(() => {});
    return () => url && URL.revokeObjectURL(url);
  }, [id]);
  return src ? <img src={src} alt="Chelenj rasmi" loading="lazy" /> : <div className="skeleton" style={{ aspectRatio: "1" }} />;
}

function Card({ e, onVote, busy }) {
  const badge = e.rank <= 3 ? RANK_BADGE[e.rank] : null;
  return (
    <div className={`photo-card ${e.rank === 1 ? "lead" : ""}`}>
      <div className="photo-img">
        <Thumb id={e.id} />
        {badge ? (
          <span className="photo-rank" style={{ background: badge.color }}><badge.icon size={13} /> {e.rank}</span>
        ) : (
          <span className="photo-rank ghost">#{e.rank}</span>
        )}
      </div>
      <div className="photo-foot">
        <span className="photo-author"><Avatar name={e.author} size={22} /> {e.author}{e.me && <span className="tag" style={{ marginLeft: 4 }}>siz</span>}</span>
        <button
          className={`vote-btn ${e.voted_by_me ? "on" : ""}`} disabled={e.me || busy}
          onClick={() => onVote(e.id)} aria-label="Ovoz berish"
        >
          <Flame size={15} fill={e.voted_by_me ? "currentColor" : "none"} />
          <span className="num">{e.votes}</span>
        </button>
      </div>
    </div>
  );
}

export default function PhotoChallenge() {
  const { data, error, reload } = useLoad(api.photos);
  const [run, busy] = useAction(reload);
  const fileRef = useRef(null);

  const onPick = (ev) => {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (file) run(() => uploadPhoto(file), "Rasm yuborildi 🔥");
  };

  if (error && !data) return null; // chelenj bo'lmasa — jim
  return (
    <div className="challenge">
      <div className="challenge-head">
        <div>
          <b><Camera size={15} /> {data?.title || "Tonggi rasm chelenji"}</b>
          <small className="muted">{data?.theme ? `Mavzu: ${data.theme}` : "Eng yaxshi kadr — 🔥 ko'p yig'adi"}</small>
        </div>
        {data && (
          <button className="btn btn-primary btn-sm" disabled={!data.can_add || busy} onClick={() => fileRef.current?.click()}>
            <ImagePlus size={16} /> {data.can_add ? `Rasm (${data.my_count}/${data.max})` : "Limit to'ldi"}
          </button>
        )}
        <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={onPick} />
      </div>

      {!data && !error && <div className="photo-grid"><Skeleton height={150} /><Skeleton height={150} /></div>}
      {data && data.entries.length === 0 && (
        <Empty icon={Camera} title="Hali rasm yo'q" text="Birinchi bo'lib bugungi kadringizni yuboring." />
      )}
      {data && data.entries.length > 0 && (
        <div className="photo-grid">
          {data.entries.map((e) => <Card key={e.id} e={e} busy={busy} onVote={(id) => { sound.pop(); run(() => api.votePhoto(id)); }} />)}
        </div>
      )}
    </div>
  );
}
