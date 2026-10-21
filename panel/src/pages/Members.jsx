import { useEffect, useState } from "react";
import { Search, Users } from "lucide-react";
import { api } from "../api.js";
import { go } from "../router.js";
import {
  Empty, ErrorBox, MEMBER_STATUS, PageHead, Person, Seg, Skeleton, StatusPill, StrikeDots, TODAY_STATUS, useLoad,
} from "../ui.jsx";
import MemberDrawer from "./MemberDrawer.jsx";

function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export default function Members({ params }) {
  const [q, setQ] = useState("");
  const [gender, setGender] = useState("");
  const [status, setStatus] = useState(params.status || "");
  const [cohort, setCohort] = useState("");
  const squad = params.squad || "";
  const open = params.open ? Number(params.open) : null;
  const query = useDebounced(q);

  const { data: cohorts } = useLoad(api.cohorts);
  const { data, error, reload } = useLoad(
    () => api.members({ q: query, gender, status, cohort, squad }),
    [query, gender, status, cohort, squad],
  );
  const items = data?.items;
  const maxStrikes = data?.max_strikes || 3;

  const setOpen = (id) => go("members", { ...params, open: id });
  const closeDrawer = () => {
    const { open: _, ...rest } = params;
    go("members", Object.keys(rest).length ? rest : undefined);
  };

  return (
    <>
      <PageHead title="Ishtirokchilar" sub={`${items ? items.length : "…"} kishi${squad ? " · tanlangan rota" : ""}`}>
        {squad && <button className="btn btn-outline btn-sm" onClick={() => go("members")}>Rota filtrini olib tashlash</button>}
      </PageHead>

      <div className="card card-pad" style={{ marginBottom: 16 }}>
        <div className="row" style={{ flexWrap: "wrap", gap: 12 }}>
          <div className="search" style={{ flex: "1 1 240px" }}>
            <Search size={16} />
            <input className="input" placeholder="Ism, @username yoki Telegram ID" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <select className="select" style={{ width: "auto" }} value={cohort} onChange={(e) => setCohort(e.target.value)}>
            <option value="">Barcha faol oqimlar</option>
            {cohorts?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <Seg value={gender} onChange={setGender} options={[{ value: "", label: "Hammasi" }, { value: "M", label: "Yigitlar" }, { value: "F", label: "Qizlar" }]} />
          <Seg value={status} onChange={setStatus} options={[
            { value: "", label: "Har qanday" }, { value: "active", label: "Faol" }, { value: "expelled", label: "Chiqarilgan" }, { value: "mentor", label: "Mentor" },
          ]} />
        </div>
      </div>

      {error && <ErrorBox text={error} />}
      <div className="card">
        {!items ? <div className="card-pad"><Skeleton height={300} /></div> : !items.length ? (
          <Empty icon={Users} title="Hech kim topilmadi" text="Filtrlarni o'zgartirib ko'ring." />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Ishtirokchi</th>
                  <th>Rota</th>
                  <th>Bugun</th>
                  <th>Ogohlantirish</th>
                  <th className="hide-sm">Immunitet</th>
                  <th className="hide-sm">Budilnik</th>
                  <th>Holati</th>
                </tr>
              </thead>
              <tbody>
                {items.map((m) => (
                  <tr key={m.id} className="click" onClick={() => setOpen(m.id)}>
                    <td><Person user={m.user} /></td>
                    <td><b>{m.squad?.name || "—"}</b><div className="muted small">{m.tribe}</div></td>
                    <td><StatusPill map={TODAY_STATUS} value={m.today} /></td>
                    <td><StrikeDots count={m.strikes} max={maxStrikes} /></td>
                    <td className="hide-sm num">{m.immunities}</td>
                    <td className="hide-sm num">{m.start_wake_time} → {m.target_wake_time}</td>
                    <td><StatusPill map={MEMBER_STATUS} value={m.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {open && <MemberDrawer id={open} onClose={closeDrawer} onChanged={reload} />}
    </>
  );
}
