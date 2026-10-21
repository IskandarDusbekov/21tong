import { useMemo, useRef, useState } from "react";
import { MessageSquareText, RotateCcw, Save, Search } from "lucide-react";
import { api } from "../api.js";
import { Empty, ErrorBox, PageHead, Pill, Skeleton, TgBubble, useAction, useConfirm, useLoad } from "../ui.jsx";

// Oldindan ko'rish uchun namunaviy qiymatlar
const SAMPLE = {
  day: 8, time: "06:30", phrase: "Erta turgan yutadi. Bugun men yutaman.", deadline: "06:35", minutes: 5,
  name: "Aziz", count: 2, reason: "vaqtida turmadi", squad: "1-rota", tribe: "07:00 Qabilasi (Yigitlar)",
  cohort: "Noyabr oqimi", start_date: "2026-11-02", invite: "Rota guruhiga kiring: https://t.me/+namuna",
  link: "https://t.me/+namuna", gender: "Yigit", goal: "Har kuni 5:30 da turish", current: "07:00", target: "05:30",
  strikes: 1, immunities: 1, done: 6, total: 7, description: "Tana yangi rejimga moslashdi.", icon: "🎙",
};

const render = (text, vars) => text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));

export default function Messages() {
  const confirm = useConfirm();
  const { data, error, setData } = useLoad(api.messages);
  const [selected, setSelected] = useState(null);
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const area = useRef();

  const items = data?.items || [];
  const current = items.find((m) => m.key === selected) || null;
  const filtered = items.filter((m) => !q || (m.title + m.text).toLowerCase().includes(q.toLowerCase()));
  const groups = [...new Set(filtered.map((m) => m.group))];

  const pick = (m) => { setSelected(m.key); setDraft(m.text); };
  const replace = (msg) => setData({ ...data, items: data.items.map((m) => (m.key === msg.key ? msg : m)) });
  const [run, busy] = useAction((msg) => { if (msg) { replace(msg); setDraft(msg.text); } });

  const vars = useMemo(() => ({ ...SAMPLE, ...(data?.settings_vars || {}) }), [data]);
  const variants = draft.split("\n---\n");

  const insert = (v) => {
    const el = area.current;
    const token = `{${v}}`;
    const pos = el?.selectionStart ?? draft.length;
    const next = draft.slice(0, pos) + token + draft.slice(el?.selectionEnd ?? pos);
    setDraft(next);
    requestAnimationFrame(() => { el?.focus(); el?.setSelectionRange(pos + token.length, pos + token.length); });
  };

  const reset = async () => {
    if (await confirm({ title: "Standart matnga qaytarasizmi?", text: "Siz yozgan matn o'chadi va dastlabki matn tiklanadi.", confirm: "Qaytarish" })) {
      run(() => api.resetMessage(current.key), "Standart matn tiklandi.");
    }
  };

  if (error) return <ErrorBox text={error} />;
  if (!data) return <Skeleton height={500} />;
  const dirty = current && draft !== current.text;
  const changedCount = items.filter((m) => m.changed).length;

  return (
    <>
      <PageHead title="Bot matnlari" sub={`Botning ${items.length} ta xabari. ${changedCount} tasi o'zgartirilgan. O'zgarish botga 30 soniyada yetib boradi.`} />
      <div className="msg-layout">
        <div className="card msg-list">
          <div style={{ padding: 12, borderBottom: "1px solid var(--line)" }}>
            <div className="search"><Search size={15} /><input className="input" placeholder="Qidirish…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          </div>
          {groups.map((g) => (
            <div key={g}>
              <div className="msg-group">{g}</div>
              {filtered.filter((m) => m.group === g).map((m) => (
                <button key={m.key} className={`msg-item ${selected === m.key ? "on" : ""}`} onClick={() => pick(m)}>
                  <span>{m.title}</span>
                  {m.changed && <i className="dot" style={{ color: "var(--sun)" }} title="O'zgartirilgan" />}
                </button>
              ))}
            </div>
          ))}
        </div>

        {!current ? (
          <div className="card"><Empty icon={MessageSquareText} title="Xabarni tanlang" text="Chapdagi ro'yxatdan tahrirlamoqchi bo'lgan xabarni tanlang." /></div>
        ) : (
          <div className="stack">
            <div className="card">
              <div className="card-head">
                <div><h2>{current.title}</h2><p><code>{current.key}</code> · {current.group}</p></div>
                {current.changed ? <Pill tone="sun">O'zgartirilgan</Pill> : <Pill>Standart</Pill>}
              </div>
              <div className="card-pad stack">
                <textarea ref={area} className="textarea" style={{ minHeight: 200 }} value={draft} onChange={(e) => setDraft(e.target.value)} />
                <div>
                  <div className="label">O'zgaruvchilar — bosing, matnga qo'shiladi</div>
                  <div className="var-chips">
                    {[...current.variables, ...Object.keys(data.settings_vars)].map((v) => (
                      <button key={v} type="button" onClick={() => insert(v)} title={`Namuna: ${vars[v]}`}>{`{${v}}`}</button>
                    ))}
                  </div>
                  <div className="muted small" style={{ marginTop: 8 }}>
                    Formatlash: <code>&lt;b&gt;</code> qalin, <code>&lt;i&gt;</code> kursiv, <code>&lt;blockquote&gt;</code> iqtibos.
                    {current.key === "alarm" && <> Bir nechta variant uchun ularni alohida qatordagi <code>---</code> bilan ajrating — bot tasodifiysini yuboradi.</>}
                  </div>
                </div>
                <div className="row" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
                  {current.changed && <button className="btn btn-ghost" disabled={busy} onClick={reset}><RotateCcw size={15} /> Standartga qaytarish</button>}
                  {dirty && <button className="btn btn-ghost" onClick={() => setDraft(current.text)}>Bekor qilish</button>}
                  <button className="btn btn-primary" disabled={busy || !dirty} onClick={() => run(() => api.saveMessage(current.key, draft), "Xabar saqlandi.")}>
                    <Save size={15} /> Saqlash
                  </button>
                </div>
              </div>
            </div>
            <div className="card">
              <div className="card-head"><h3>Telegram'da shunday ko'rinadi</h3><span className="muted small">namunaviy qiymatlar bilan</span></div>
              <div className="card-pad">
                <div className="tg-preview stack" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {variants.map((v, i) => <TgBubble key={i} html={render(v.trim(), vars)} />)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
