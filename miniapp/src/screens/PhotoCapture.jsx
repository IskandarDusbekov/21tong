// Iliq suv rasmi — jonli kameradan to'g'ridan-to'g'ri (galereyadan tanlab bo'lmaydi).
// Shunda eski rasmni yuborib aldab bo'lmaydi: rasm shu yerda, shu payt olinadi.
import { useEffect, useRef, useState } from "react";
import { Camera, RotateCcw, Send, X } from "lucide-react";
import { uploadWater } from "../api.js";
import { useToast } from "../ui.jsx";

export default function PhotoCapture({ onClose, onDone }) {
  const liveRef = useRef(null);
  const streamRef = useRef(null);
  const [phase, setPhase] = useState("init"); // init | ready | shot | uploading | error
  const [blob, setBlob] = useState(null);
  const [url, setUrl] = useState(null);
  const [err, setErr] = useState("");
  const toast = useToast();

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
        if (!active) { stream.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = stream;
        if (liveRef.current) liveRef.current.srcObject = stream;
        setPhase("ready");
      } catch {
        setErr("Kameraga ruxsat berilmadi. Rasmga olish uchun kamerani yoqing.");
        setPhase("error");
      }
    })();
    return () => { active = false; streamRef.current?.getTracks().forEach((t) => t.stop()); };
  }, []);
  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);

  const snap = () => {
    const v = liveRef.current;
    if (!v?.videoWidth) return;
    const max = 1600;
    const scale = Math.min(1, max / Math.max(v.videoWidth, v.videoHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(v.videoWidth * scale);
    canvas.height = Math.round(v.videoHeight * scale);
    canvas.getContext("2d").drawImage(v, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((b) => {
      if (!b) return;
      setBlob(b);
      setUrl(URL.createObjectURL(b));
      setPhase("shot");
    }, "image/jpeg", 0.85);
  };

  const retake = () => {
    if (url) URL.revokeObjectURL(url);
    setBlob(null); setUrl(null); setPhase("ready");
  };

  const send = async () => {
    setPhase("uploading");
    try {
      await uploadWater(blob);
      toast("Iliq suv qabul qilindi — tanga berildi!");
      onDone?.();
    } catch (e) {
      toast(e.message || "Rasm yuborilmadi", "error");
      setPhase("shot");
    }
  };

  return (
    <div className="recorder">
      <button className="recorder-close" onClick={onClose} aria-label="Yopish"><X size={22} /></button>
      <div className="recorder-stage">
        {phase === "shot" || phase === "uploading" ? (
          <img className="recorder-video" src={url} alt="Iliq suv" />
        ) : (
          <video ref={liveRef} className="recorder-video" muted playsInline autoPlay />
        )}
      </div>
      <div className="recorder-controls">
        {phase === "error" && <p className="recorder-err">{err}</p>}
        {phase === "init" && <p className="recorder-hint">Kamera ochilmoqda…</p>}
        {phase === "ready" && (
          <>
            <p className="recorder-hint">Stakandagi iliq suvni kadr ichiga oling va tugmani bosing.</p>
            <button className="recorder-rec recorder-shot" onClick={snap} aria-label="Rasmga olish"><Camera size={26} /></button>
          </>
        )}
        {(phase === "shot" || phase === "uploading") && (
          <div className="recorder-actions">
            <button className="btn btn-soft" disabled={phase === "uploading"} onClick={retake}><RotateCcw size={17} /> Qayta</button>
            <button className="btn btn-primary" disabled={phase === "uploading"} onClick={send}>
              <Send size={17} /> {phase === "uploading" ? "Yuborilmoqda…" : "Yuborish"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
