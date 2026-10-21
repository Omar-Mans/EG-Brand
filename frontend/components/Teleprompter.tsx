"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Post, Talk } from "@/lib/types";

/** Full-screen teleprompter. Optional front camera recording while the script scrolls (text sits near the lens). */
export default function Teleprompter({ talk, postId, onClose, onSaved }: {
  talk: Talk; postId: string; onClose: () => void; onSaved: (p: Post) => void;
}) {
  const lines = [talk.hook, ...talk.lines, talk.cta].filter(Boolean);
  const words = lines.join(" ").split(/\s+/).length;
  const scroller = useRef<HTMLDivElement>(null);
  const cam = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const raf = useRef(0);
  const [wpm, setWpm] = useState(140);
  const [size, setSize] = useState(40);
  const [mirror, setMirror] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [count, setCount] = useState(0);
  const [camera, setCamera] = useState(false);
  const [recording, setRecording] = useState(false);
  const [take, setTake] = useState<{ url: string; blob: Blob } | null>(null);
  const [status, setStatus] = useState("");

  const stopScroll = useCallback(() => { cancelAnimationFrame(raf.current); setPlaying(false); }, []);

  const startScroll = useCallback(() => {
    const el = scroller.current;
    if (!el) return;
    const travel = el.scrollHeight - el.clientHeight;
    const seconds = (words / wpm) * 60;
    const pxPerMs = travel / (seconds * 1000);
    let last = performance.now();
    let pos = el.scrollTop; // keep the exact position: browsers round scrollTop, and tiny steps would never move
    const tick = (now: number) => {
      pos = Math.min(travel, pos + pxPerMs * (now - last));
      el.scrollTop = pos;
      last = now;
      if (pos < travel) raf.current = requestAnimationFrame(tick);
      else setPlaying(false);
    };
    setPlaying(true);
    raf.current = requestAnimationFrame(tick);
  }, [words, wpm]);

  const countdown = (then: () => void) => {
    setCount(3);
    let n = 3;
    const t = setInterval(() => {
      n -= 1;
      setCount(n);
      if (n === 0) { clearInterval(t); then(); }
    }, 1000);
  };

  async function toggleCamera() {
    if (camera) {
      stream.current?.getTracks().forEach((t) => t.stop());
      stream.current = null;
      setCamera(false);
      return;
    }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1080 }, height: { ideal: 1920 } }, audio: { echoCancellation: true, noiseSuppression: true },
      });
      setCamera(true);
      setStatus("");
    } catch {
      setStatus("مقدرناش نفتح الكاميرا. اسمح للمتصفح يستخدمها، أو صوّر بكاميرا الموبايل وارفع الفيديو.");
    }
  }
  useEffect(() => { if (camera && cam.current && stream.current) cam.current.srcObject = stream.current; }, [camera]);

  function record() {
    if (!stream.current) return;
    const type = ["video/mp4", "video/webm;codecs=vp9,opus", "video/webm"].find((t) => MediaRecorder.isTypeSupported(t)) || "";
    chunks.current = [];
    const r = new MediaRecorder(stream.current, type ? { mimeType: type } : undefined);
    r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
    r.onstop = () => {
      const blob = new Blob(chunks.current, { type: (r.mimeType || "video/webm").split(";")[0] });
      setTake({ url: URL.createObjectURL(blob), blob });
    };
    recorder.current = r;
    if (scroller.current) scroller.current.scrollTop = 0;
    countdown(() => { r.start(1000); setRecording(true); startScroll(); });
  }
  function stopRecording() {
    recorder.current?.stop();
    setRecording(false);
    stopScroll();
  }

  async function saveTake() {
    if (!take) return;
    setStatus("بنرفع اللقطة…");
    try {
      const form = new FormData();
      const ext = take.blob.type.includes("mp4") ? "mp4" : "webm";
      form.append("file", new File([take.blob], `take.${ext}`, { type: take.blob.type }));
      onSaved(await api<Post>(`/api/posts/${postId}/reel/raw`, { form }));
      setStatus("اتحفظت ✓ هتلاقيها تحت السكريبت");
      URL.revokeObjectURL(take.url);
      setTake(null);
    } catch (e: any) { setStatus(e.message); }
  }

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === " " && !recording) { e.preventDefault(); playing ? stopScroll() : startScroll(); }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose, playing, recording, startScroll, stopScroll]);
  useEffect(() => () => { // on close only: stop the scroll and release the camera
    cancelAnimationFrame(raf.current);
    stream.current?.getTracks().forEach((t) => t.stop());
  }, []);

  return (
    <div className="prompter" role="dialog" aria-modal="true" aria-label="شاشة التلقين">
      {camera && <video ref={cam} className="prompter-cam" muted autoPlay playsInline />}
      <div ref={scroller} className={`prompter-text ${camera ? "over-cam" : ""}`} style={{ fontSize: size, transform: mirror ? "scaleX(-1)" : undefined }}
        onClick={() => !recording && (playing ? stopScroll() : startScroll())}>
        <div className="prompter-pad pad-top" />
        {lines.map((l, i) => <p key={i} className={i === 0 ? "hook" : i === lines.length - 1 ? "cta" : ""}>{l}</p>)}
        <div className="prompter-pad pad-end" />
      </div>
      <div className="prompter-guide" aria-hidden="true" />
      {count > 0 && <div className="prompter-count" aria-live="assertive">{count}</div>}
      {recording && <span className="prompter-rec">● REC</span>}

      {take ? (
        <div className="prompter-take">
          <video src={take.url} controls playsInline />
          <div className="row">
            <button className="btn primary" type="button" onClick={saveTake}>احفظ اللقطة</button>
            <a className="btn" href={take.url} download="take">نزّلها</a>
            <button className="btn" type="button" onClick={() => { URL.revokeObjectURL(take.url); setTake(null); }}>صوّر تاني</button>
          </div>
        </div>
      ) : (
        <div className="prompter-bar">
          {!recording && <button className="btn sm" type="button" onClick={() => (playing ? stopScroll() : countdown(startScroll))}>{playing ? "إيقاف" : "ابدأ"}</button>}
          {!recording && <button className="btn sm" type="button" onClick={() => { stopScroll(); if (scroller.current) scroller.current.scrollTop = 0; }}>من الأول</button>}
          <label className="prompter-ctl">السرعة <input type="range" min={90} max={220} step={10} value={wpm} onChange={(e) => setWpm(+e.target.value)} aria-label="سرعة القراءة" /><span>{wpm}</span></label>
          <label className="prompter-ctl">الخط <input type="range" min={26} max={72} step={2} value={size} onChange={(e) => setSize(+e.target.value)} aria-label="حجم الخط" /></label>
          <button className="btn sm" type="button" aria-pressed={mirror} onClick={() => setMirror(!mirror)}>مرآة</button>
          <button className="btn sm" type="button" aria-pressed={camera} onClick={toggleCamera} disabled={recording}>{camera ? "اقفل الكاميرا" : "صوّر من هنا"}</button>
          {camera && !recording && <button className="btn sm primary" type="button" onClick={record}>● سجّل</button>}
          {recording && <button className="btn sm primary" type="button" onClick={stopRecording}>■ وقّف التسجيل</button>}
          <button className="btn sm" type="button" onClick={onClose} disabled={recording}>اقفل</button>
        </div>
      )}
      {status && <p className="prompter-status" aria-live="polite">{status}</p>}
    </div>
  );
}
