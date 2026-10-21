import { useState } from "react";
import { LogIn, Sunrise } from "lucide-react";
import { api } from "../api.js";
import { ErrorBox } from "../ui.jsx";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await api.login(username, password));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand">
          <div className="brand-mark"><Sunrise size={20} color="#fff" /></div>
          <div><b>21 Tong</b><small>Qo'mondonlik paneli</small></div>
        </div>
        <h1 style={{ marginBottom: 6 }}>Xush kelibsiz</h1>
        <p className="muted" style={{ marginTop: 0, marginBottom: 20 }}>Admin login va parolingiz bilan kiring.</p>
        {error && <ErrorBox text={error} />}
        <div className="field" style={{ marginBottom: 14 }}>
          <label htmlFor="u">Login</label>
          <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus />
        </div>
        <div className="field" style={{ marginBottom: 20 }}>
          <label htmlFor="p">Parol</label>
          <input id="p" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </div>
        <button className="btn btn-primary" style={{ width: "100%", padding: 11 }} disabled={busy || !username || !password}>
          <LogIn size={17} /> Kirish
        </button>
      </form>
    </div>
  );
}
