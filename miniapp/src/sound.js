// Yengil ovoz belgilari — Web Audio orqali (fayl yuklanmaydi). Ovozsiz rejim localStorage'da saqlanadi.
const KEY = "21tong.muted";

let ctx = null;
let muted = (() => {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
})();

const listeners = new Set();

function ensureCtx() {
  if (!ctx) {
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch {
      ctx = null;
    }
  }
  if (ctx?.state === "suspended") ctx.resume().catch(() => {});
  return ctx;
}

/** Bitta nota. t — boshlanish (soniya), freq — chastota, dur — davomiylik. */
function tone(freq, start, dur, { type = "sine", gain = 0.14 } = {}) {
  const ac = ensureCtx();
  if (!ac) return;
  const osc = ac.createOscillator();
  const vol = ac.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  const t0 = ac.currentTime + start;
  vol.gain.setValueAtTime(0, t0);
  vol.gain.linearRampToValueAtTime(gain, t0 + 0.02);
  vol.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  osc.connect(vol).connect(ac.destination);
  osc.start(t0);
  osc.stop(t0 + dur + 0.02);
}

function play(notes) {
  if (muted) return;
  notes.forEach(([freq, start, dur, opts]) => tone(freq, start, dur, opts));
}

// Notalar (Hz): C5 523, E5 659, G5 784, C6 1046, A5 880, D6 1175
export const sound = {
  get muted() {
    return muted;
  },
  toggle() {
    muted = !muted;
    try {
      localStorage.setItem(KEY, muted ? "1" : "0");
    } catch {
      /* private rejim */
    }
    if (!muted) sound.pop();
    listeners.forEach((fn) => fn(muted));
    return muted;
  },
  onChange(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
  // Uyg'onish marosimi — ko'tariluvchi arpejio
  wake() {
    play([[523, 0, 0.5], [659, 0.12, 0.5], [784, 0.24, 0.6], [1046, 0.38, 0.8, { gain: 0.16 }]]);
  },
  // Muvaffaqiyat — ikki nota
  success() {
    play([[659, 0, 0.35], [988, 0.1, 0.45]]);
  },
  // Qisqa bosish (ovoz berish, tugma)
  pop() {
    play([[880, 0, 0.14, { type: "triangle", gain: 0.1 }]]);
  },
  // Bosqich — qisqa fanfara
  stage() {
    play([[523, 0, 0.4], [659, 0.12, 0.4], [784, 0.24, 0.4], [1046, 0.36, 0.7, { gain: 0.17 }], [1318, 0.5, 0.9, { gain: 0.15 }]]);
  },
};
