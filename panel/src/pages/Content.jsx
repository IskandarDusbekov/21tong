import { useState } from "react";
import { Award, Crown, Flame, Medal, Mountain, Plus, Quote, Shield, Sprout, Star, Trash2 } from "lucide-react";
import { api } from "../api.js";
import { ErrorBox, PageHead, Seg, Skeleton, Switch, useAction, useConfirm, useLoad } from "../ui.jsx";

const STAGE_ICONS = { sprout: Sprout, mountain: Mountain, shield: Shield, crown: Crown, flame: Flame, star: Star, medal: Medal };

function Phrases() {
  const confirm = useConfirm();
  const { data, error, reload, setData } = useLoad(api.phrases);
  const [text, setText] = useState("");
  const [run, busy] = useAction(reload);

  const add = (e) => {
    e.preventDefault();
    run(() => api.addPhrase(text), "Gap qo'shildi.").then((r) => r && setText(""));
  };
  const patch = (p, body) => {
    setData(data.map((x) => (x.id === p.id ? { ...x, ...body } : x)));
    api.updatePhrase(p.id, body).catch(reload);
  };
  const remove = async (p) => {
    if (await confirm({ title: "Gapni o'chirasizmi?", text: p.text, confirm: "O'chirish", danger: true })) run(() => api.deletePhrase(p.id), "O'chirildi.");
  };

  if (error) return <ErrorBox text={error} />;
  if (!data) return <Skeleton height={300} />;
  const active = data.filter((p) => p.is_active).length;
  return (
    <div className="card">
      <div className="card-head">
        <div><h2>O'qiladigan gaplar</h2><p>Har kuni uyg'ongach har kimga tasodifiy bittasi beriladi · {active} ta faol</p></div>
      </div>
      <form className="row" style={{ padding: "14px 20px", borderBottom: "1px solid var(--line)" }} onSubmit={add}>
        <input className="input" placeholder="Yangi gap, masalan: Men bugun ham o'z so'zimda turaman." value={text} onChange={(e) => setText(e.target.value)} maxLength={200} />
        <button className="btn btn-primary" disabled={busy || !text.trim()}><Plus size={16} /> Qo'shish</button>
      </form>
      <ul className="list-edit">
        {data.map((p) => (
          <li key={p.id} className={p.is_active ? "" : "off"}>
            <Quote size={15} color="var(--sun)" style={{ flex: "none" }} />
            <input className="input" defaultValue={p.text} onBlur={(e) => e.target.value !== p.text && patch(p, { text: e.target.value })} maxLength={200} />
            <Switch on={p.is_active} onChange={(v) => patch(p, { is_active: v })} label="Faol" />
            <button className="btn btn-ghost btn-icon" onClick={() => remove(p)} aria-label="O'chirish"><Trash2 size={16} /></button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Stages() {
  const confirm = useConfirm();
  const { data, error, reload, setData } = useLoad(api.stages);
  const { data: icons } = useLoad(api.stageIcons);
  const [run, busy] = useAction(reload);

  const patch = (s, body) => {
    setData(data.map((x) => (x.id === s.id ? { ...x, ...body } : x)));
    api.updateStage(s.id, body).catch(reload);
  };
  const add = () => {
    const day = Math.max(0, ...data.map((s) => s.day)) + 10;
    run(() => api.addStage({ day, name: "Yangi bosqich", description: "", icon: "star" }), "Bosqich qo'shildi.");
  };
  const remove = async (s) => {
    if (await confirm({ title: `«${s.name}» bosqichini o'chirasizmi?`, text: "Bu bosqich Mini App va botdan olib tashlanadi.", confirm: "O'chirish", danger: true })) {
      run(() => api.deleteStage(s.id), "O'chirildi.");
    }
  };

  if (error) return <ErrorBox text={error} />;
  if (!data) return <Skeleton height={300} />;
  return (
    <div className="card">
      <div className="card-head">
        <div><h2>Bosqichlar</h2><p>Ishtirokchi shuncha kunni o'tkazsa — yangi bosqich va bot tabrigi</p></div>
        <button className="btn btn-outline btn-sm" disabled={busy} onClick={add}><Plus size={15} /> Bosqich</button>
      </div>
      <ul className="list-edit">
        {data.map((s) => {
          const Icon = STAGE_ICONS[s.icon] || Award;
          return (
            <li key={s.id} style={{ alignItems: "flex-start", flexWrap: "wrap" }}>
              <div className="kpi-icon tone-sun" style={{ width: 40, height: 40 }}><Icon size={19} /></div>
              <div style={{ flex: "1 1 260px", minWidth: 0 }}>
                <div className="row" style={{ gap: 6 }}>
                  <input type="number" className="input num" style={{ width: 70, fontWeight: 700 }} defaultValue={s.day} min={1}
                    onBlur={(e) => Number(e.target.value) !== s.day && patch(s, { day: Number(e.target.value) })} />
                  <span className="muted small">-kun</span>
                  <input className="input" style={{ fontWeight: 600 }} defaultValue={s.name} onBlur={(e) => e.target.value !== s.name && patch(s, { name: e.target.value })} />
                </div>
                <input className="input small" style={{ marginTop: 4 }} placeholder="Tavsif — bot tabrigida va Mini App'da ko'rinadi" defaultValue={s.description}
                  onBlur={(e) => e.target.value !== s.description && patch(s, { description: e.target.value })} />
                <div className="icon-pick" style={{ marginTop: 8, paddingLeft: 12 }}>
                  {(icons || []).map((ic) => {
                    const I = STAGE_ICONS[ic.value] || Award;
                    return <button key={ic.value} type="button" className={s.icon === ic.value ? "on" : ""} title={ic.label} onClick={() => patch(s, { icon: ic.value })}><I size={15} /></button>;
                  })}
                </div>
              </div>
              <button className="btn btn-ghost btn-icon" onClick={() => remove(s)} aria-label="O'chirish"><Trash2 size={16} /></button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function Content() {
  const [tab, setTab] = useState("phrases");
  return (
    <>
      <PageHead title="Gaplar va bosqichlar" sub="O'zgarishlar avtomatik saqlanadi.">
        <Seg value={tab} onChange={setTab} options={[{ value: "phrases", label: "O'qiladigan gaplar" }, { value: "stages", label: "Bosqichlar" }]} />
      </PageHead>
      {tab === "phrases" ? <Phrases /> : <Stages />}
    </>
  );
}
