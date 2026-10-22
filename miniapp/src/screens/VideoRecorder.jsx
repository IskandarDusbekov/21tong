// Mini App ichida video raport yozish: kameradan to'g'ridan-to'g'ri, 10 soniyagacha.
// Tashqarida, yurib turib gapni o'qib yoziladi; so'ng serverga yuklanadi.
import { useEffect, useRef, useState } from "react";
import { RotateCcw, Send, Square, Video, X } from "lucide-react";
import { uploadVideo } from "../api.js";
import { useToast } from "../ui.jsx";

const MAX_SEC = 10;

function pickMime() {
  const types = ["video/mp4", "video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
  for (const t of types) {
    if (window.MediaRecorder?.isTypeSupported?.(t)) return t;
  }
  return "";
}

export default function VideoRecorder({ onClose, onDone }) {
  const liveRef = useRef(null);
  const streamRef = useRef(null);
  const recRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const [phase, setPhase] = useState("init"); // init | ready | recording | recorded | uploading | error
  const [elapsed, setElapsed] = useState(0);
  const [blob, setBlob] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [err, setErr] = useState("");
  const toast = useToast();

  // Kamerani ochish (orqa kamera, ovoz bilan)
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } }, audio: true,
        });
        if (!active) { stream.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = stream;
        if (liveRef.current) liveRef.current.srcObject = stream;
        setPhase("ready");
      } catch {
        setErr("Kameraga ruxsat berilmadi yoki kamera topilmadi. Brauzer sozlamalaridan ruxsat bering.");
        setPhase("error");
      }
    })();
    return () => {
      active = false;
      clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  useEffect(() => () => previewUrl && URL.revokeObjectURL(previewUrl), [previewUrl]);

  const stop = () => {
    clearInterval(timerRef.current);
    if (recRef.current && recRef.current.state !== "inactive") recRef.current.stop();
  };

  const start = () => {
    chunksRef.current = [];
    const mime = pickMime();
    const rec = new MediaRecorder(streamRef.current, mime ? { mimeType: mime } : undefined);
    recRef.current = rec;
    rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
    rec.onstop = () => {
      const b = new Blob(chunksRef.current, { type: mime || "video/webm" });
      setBlob(b);
      setPreviewUrl(URL.createObjectURL(b));
      setPhase("recorded");
    };
    rec.start();
    setElapsed(0);
    setPhase("recording");
    timerRef.current = setInterval(() => {
      setElapsed((s) => {
        if (s + 1 >= MAX_SEC) { stop(); return MAX_SEC; }
        return s + 1;
      });
    }, 1000);
  };

  const retake = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setBlob(null); setPreviewUrl(null); setElapsed(0); setPhase("ready");
  };

  const send = async () => {
    setPhase("uploading");
    try {
      await uploadVideo(blob, elapsed || MAX_SEC);
      toast("Video yuborildi — rota tekshiradi");
      onDone?.();
    } catch (e) {
      toast(e.message || "Video yuborilmadi", "error");
      setPhase("recorded");
    }
  };

  return (
    <div className="recorder">
      <button className="recorder-close" onClick={onClose} aria-label="Yopish"><X size={22} /></button>
      <div className="recorder-stage">
        {phase === "recorded" || phase === "uploading" ? (
          <video className="recorder-video" src={previewUrl} controls playsInline autoPlay loop />
        ) : (
          <video ref={liveRef} className="recorder-video mirror-off" muted playsInline autoPlay />
        )}
        {phase === "recording" && <div className="recorder-timer num">{MAX_SEC - elapsed}</div>}
      </div>

      <div className="recorder-controls">
        {phase === "error" && <p className="recorder-err">{err}</p>}
        {phase === "init" && <p className="recorder-hint">Kamera ochilmoqda…</p>}
        {phase === "ready" && (
          <>
            <p className="recorder-hint">
              Tashqariga chiqing. Yurib turib gapni o'qing — {MAX_SEC} soniyagacha.<br />
              <span className="recorder-note"><Video size={12} /> Rotadan 3 kishi tekshiradi.</span>
            </p>
            <button className="recorder-rec" onClick={start} aria-label="Yozishni boshlash"><span /></button>
          </>
        )}
        {phase === "recording" && (
          <button className="recorder-stop" onClick={stop} aria-label="To'xtatish"><Square size={20} fill="currentColor" /></button>
        )}
        {(phase === "recorded" || phase === "uploading") && (
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
