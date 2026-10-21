import { ChevronRight, Users, Wrench } from "lucide-react";
import { api } from "../api.js";
import { Avatar, Empty, ErrorCard, Skeleton, useLoad } from "../ui.jsx";

const STATUS = { pending: ["Tasdiq kutmoqda", "sun"], rejected: ["Rad etilgan", "bad"], new: ["Yangi", ""] };

export default function DevLogin({ onPick }) {
  const { data, error } = useLoad(api.devUsers);
  const groups = [["M", "Yigitlar"], ["F", "Qizlar"]];
  return (
    <div className="app">
      <div className="screen-head">
        <div>
          <h2>Dev kirish</h2>
          <p className="muted small">Telegram'siz lokal ko'rish. Kim sifatida kirasiz?</p>
        </div>
        <div className="window-icon"><Wrench size={18} /></div>
      </div>
      {error && <ErrorCard text={error} />}
      {!data && !error && <Skeleton height={240} />}
      {data?.length === 0 && (
        <Empty icon={Users} title="Foydalanuvchi yo'q" text="Demo ma'lumot yarating: python manage.py seed_demo" />
      )}
      {data?.length > 0 && groups.map(([g, title]) => {
        const users = data.filter((u) => u.gender === g);
        if (!users.length) return null;
        return (
          <div key={g}>
            <div className="section-title">{title}</div>
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              {users.map((u, i) => {
                const [label, tone] = STATUS[u.status] || [];
                return (
                  <button key={u.telegram_id} className="dev-user" style={i ? { borderTop: "1px solid var(--line)" } : undefined} onClick={() => onPick(u)}>
                    <Avatar name={u.name} />
                    <span className="name">{u.name}</span>
                    {label && <span className={`tag ${tone}`}>{label}</span>}
                    <small className="muted num">{u.telegram_id}</small>
                    <ChevronRight size={18} className="muted" />
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
