import { Coins, Trophy } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorCard, Skeleton, useLoad } from "../ui.jsx";

function Podium({ top }) {
  // 2-o'rin chapda, 1-o'rin markazda, 3-o'rin o'ngda
  const order = [top[1], top[0], top[2]];
  const places = [2, 1, 3];
  return (
    <div className="podium">
      {order.map((r, i) =>
        r ? (
          <div key={places[i]} className="podium-col">
            <Avatar name={r.name} />
            <div className="podium-name">{r.name}{r.me && " (siz)"}</div>
            <div className="podium-bar">
              <div style={{ fontSize: 20 }}>{places[i]}</div>
              <small className="num" style={{ color: "#fff", opacity: 0.9 }}>{r.coins}</small>
            </div>
          </div>
        ) : <div key={places[i]} />,
      )}
    </div>
  );
}

export default function Rating() {
  const { data, error } = useLoad(api.leaderboard);
  return (
    <div>
      <div className="screen-head">
        <div>
          <h2>IrodaCoin reytingi</h2>
          <p className="muted small">Qabilangiz ichida, Bounty'lar bo'yicha</p>
        </div>
        <div className="window-icon" style={{ background: "var(--sun-soft)", color: "var(--sun)" }}><Trophy size={18} /></div>
      </div>
      {error && !data && <ErrorCard text={error} />}
      {!data && !error && <Skeleton height={260} />}
      {data?.length === 0 && <Empty icon={Trophy} title="Reyting hali bo'sh" />}
      {data?.length > 0 && (
        <>
          <Podium top={data.slice(0, 3)} />
          {data.length > 3 && (
            <ol className="rank-list card">
              {data.slice(3).map((r, i) => (
                <li key={i} className={r.me ? "me" : ""}>
                  <span className="pos num">{i + 4}</span>
                  <Avatar name={r.name} />
                  <span className="name">{r.name}{r.me && " (siz)"}</span>
                  <span className="coin num"><Coins size={14} />{r.coins}</span>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  );
}
