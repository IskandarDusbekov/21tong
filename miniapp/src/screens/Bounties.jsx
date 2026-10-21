import { BookOpen, CheckCircle2, Coins, Dumbbell, Footprints, Target } from "lucide-react";
import { api } from "../api.js";
import { Empty, ErrorCard, Skeleton, useAction, useLoad } from "../ui.jsx";

// Sarlavhaga qarab mos ikonka (aks holda — nishon)
const ICON_RULES = [
  [/kitob|o'qi|bet/i, BookOpen],
  [/sport|mashq|turnik|zal/i, Dumbbell],
  [/yur|qadam|yugur/i, Footprints],
];
const iconFor = (title) => ICON_RULES.find(([re]) => re.test(title))?.[1] || Target;

export default function Bounties({ me, reloadMe }) {
  const { data, error, reload } = useLoad(api.bounties);
  const [run, busy] = useAction(() => { reload(); reloadMe(); });
  const earned = data?.filter((b) => b.done).reduce((s, b) => s + b.reward, 0) || 0;

  return (
    <div>
      <div className="screen-head">
        <div>
          <h2>Kunduzgi Bounty</h2>
          <p className="muted small">Ixtiyoriy topshiriqlar · bugun <span className="coin num"><Coins size={13} />{earned}</span> topildi</p>
        </div>
        <div className="card" style={{ padding: "8px 12px", textAlign: "center" }}>
          <span className="coin num" style={{ fontSize: 17 }}><Coins size={16} />{me?.coins ?? "–"}</span>
          <small className="muted" style={{ display: "block" }}>balans</small>
        </div>
      </div>

      {error && !data && <ErrorCard text={error} />}
      {!data && !error && <div className="stack"><Skeleton height={110} /><Skeleton height={110} /></div>}
      {data?.length === 0 && <Empty icon={Target} title="Bugun topshiriq yo'q" text="Yangi Bounty'lar admin tomonidan e'lon qilinadi." />}

      <div className="stack">
        {data?.map((b) => {
          const Icon = b.done ? CheckCircle2 : iconFor(b.title);
          return (
            <div key={b.id} className={`card bounty ${b.done ? "done" : ""}`}>
              <div className="bounty-icon"><Icon size={22} /></div>
              <div className="bounty-body">
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <b>{b.title}</b>
                  <span className="coin num"><Coins size={14} />+{b.reward}</span>
                </div>
                <p>{b.description || "Bajarib, belgilang — IrodaCoin oling."}</p>
                {b.done ? (
                  <span className="tag ok">Bajarildi</span>
                ) : (
                  <button className="btn btn-soft" disabled={busy} onClick={() => run(() => api.completeBounty(b.id), `+${b.reward} IrodaCoin`)}>
                    Bajardim
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
