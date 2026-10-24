import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type CaseView, type Health, type TurnResult } from "./api";
import { Recorder, fakeSpeak, playMp3, speakWithBrowser } from "./audio";
import { MascotScene, type MascotState } from "./components/Mascot3D";
import { ActionPlan, Countdown, IncidentCard, LiabilityMeter, useNow } from "./components/Panels";
import { DocsDrawer } from "./components/DocsDrawer";

type Bubble = { role: "user" | "agent"; text: string } | null;

const GREETING = "Hold the button and tell me what happened. Take a breath. We'll do this together.";

declare global {
  interface Window {
    __gh?: Record<string, unknown>;
  }
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [view, setView] = useState<CaseView | null>(null);
  const [mascot, setMascot] = useState<MascotState>("idle");
  const [bubble, setBubble] = useState<Bubble>({ role: "agent", text: GREETING });
  const [last, setLast] = useState<Pick<TurnResult, "tools" | "timings"> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [docsOpen, setDocsOpen] = useState(false);
  const [docsVersion, setDocsVersion] = useState(0);
  const [offsetMs, setOffsetMs] = useState(0);
  const [typed, setTyped] = useState("");
  const recorder = useRef(new Recorder());
  const busy = useRef(false);
  const caseRef = useRef<CaseView | null>(null);
  const now = useNow() + offsetMs;

  const apply = (v: CaseView) => {
    caseRef.current = v;
    setView(v);
    setOffsetMs(new Date(v.server_now).getTime() - Date.now());
  };

  useEffect(() => {
    api.health().then(setHealth).catch(() => setError("Backend offline: start it on :8000"));
  }, []);

  const ensureCase = async () => caseRef.current ?? (apply(await api.createCase()), caseRef.current!);

  const runTurn = useCallback(async (input: Blob | string) => {
    if (busy.current) return;
    busy.current = true;
    setError(null);
    setMascot("thinking");
    try {
      const c = await ensureCase();
      const res = await api.turn(c.id, input);
      setBubble({ role: "user", text: res.heard });
      apply(res.case);
      setLast({ tools: res.tools, timings: res.timings });
      setDocsVersion((n) => n + 1);
      setHealth((h) => (h ? { ...h, tts_chars_left: res.tts_chars_left } : h));
      await new Promise((r) => setTimeout(r, 900));
      setBubble({ role: "agent", text: res.reply });
      setMascot("speaking");
      window.__gh && ((window.__gh.events as unknown[]).push({ t: performance.now(), type: "reply", text: res.reply, audio: res.audio }));
      if (res.audio) await playMp3(res.audio);
      else await speakWithBrowser(res.reply);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setMascot("idle");
      busy.current = false;
    }
  }, []);

  const startTalk = async () => {
    if (busy.current) return;
    try {
      await recorder.current.start();
      setMascot("listening");
      setBubble({ role: "user", text: "Listening…" });
    } catch {
      setError("Microphone blocked. Allow mic access or type below.");
    }
  };
  const stopTalk = async () => {
    if (mascot !== "listening") return;
    const blob = await recorder.current.stop();
    if (blob.size < 1500) {
      setMascot("idle");
      setBubble({ role: "agent", text: "I didn't catch that. Hold the button while you speak." });
      return;
    }
    runTurn(blob);
  };

  // push-to-talk with the space bar
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code === "Space" && !e.repeat && document.activeElement?.tagName !== "INPUT") {
        e.preventDefault();
        startTalk();
      }
    };
    const up = (e: KeyboardEvent) => e.code === "Space" && document.activeElement?.tagName !== "INPUT" && stopTalk();
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  });

  // automation hook used to record the demo video with pre-recorded voices
  useEffect(() => {
    window.__gh = {
      events: [] as unknown[],
      say: async (url: string) => {
        setMascot("listening");
        setBubble({ role: "user", text: "Listening…" });
        const blob = await fakeSpeak(url);
        await runTurn(blob);
      },
      docs: (open: boolean) => setDocsOpen(open),
      busy: () => busy.current,
    };
  }, [runTurn]);

  const deadline = view?.golden_hour_deadline ?? null;
  const left = deadline ? new Date(deadline).getTime() - now : null;
  const ringFraction = left === null ? null : Math.max(0, Math.min(1, left / 3600000));
  const draftsReady = view && view.missing.length === 0;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src="/shield.svg" alt="" />
          <div>
            <h1>GoldenHour</h1>
            <p>Voice first-aid for the first 60 minutes after a scam</p>
          </div>
        </div>
        <div className="chips">
          <span className="chip">STT · {health?.stt ?? "…"}</span>
          <span className="chip">LLM · {health?.llm?.replace("openai/", "") ?? "…"}</span>
          <span className={`chip ${health?.tts === "elevenlabs" ? "gold" : ""}`}>
            TTS · {health?.tts === "elevenlabs" ? `ElevenLabs (${health.tts_chars_left} chars left)` : "browser"}
          </span>
          <a className="chip call" href="tel:1930">📞 1930</a>
        </div>
      </header>

      <main className="grid">
        <section className="stage clay">
          <div className="scene">
            <MascotScene state={mascot} ringFraction={ringFraction} urgent={left !== null && left < 15 * 60000} />
            <div className={`state-tag ${mascot}`}>
              {{ idle: "Kavach is ready", listening: "Listening…", thinking: "Thinking…", speaking: "Speaking" }[mascot]}
            </div>
          </div>

          <AnimatePresence mode="wait">
            {bubble && (
              <motion.div
                key={bubble.text}
                className={`bubble ${bubble.role}`}
                initial={{ y: 14, opacity: 0, scale: 0.96 }}
                animate={{ y: 0, opacity: 1, scale: 1 }}
                exit={{ y: -10, opacity: 0 }}
                transition={{ type: "spring", stiffness: 320, damping: 24 }}
              >
                <span className="who">{bubble.role === "user" ? "You" : "Kavach"}</span>
                {bubble.text}
              </motion.div>
            )}
          </AnimatePresence>

          <div className="controls">
            <motion.button
              className={`mic ${mascot === "listening" ? "live" : ""}`}
              onPointerDown={startTalk}
              onPointerUp={stopTalk}
              onPointerLeave={stopTalk}
              whileTap={{ scale: 0.92 }}
              disabled={mascot === "thinking" || mascot === "speaking"}
            >
              <span className="mic-icon">🎙️</span>
              {mascot === "listening" ? "Release to send" : "Hold to talk"}
            </motion.button>
            <form
              className="typebox"
              onSubmit={(e) => {
                e.preventDefault();
                if (typed.trim()) runTurn(typed.trim());
                setTyped("");
              }}
            >
              <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="…or type in Hindi / English" />
            </form>
          </div>

          <div className="pipeline">
            {last ? (
              <>
                {last.timings.stt_ms !== undefined && <span className="hop">🎧 Whisper {last.timings.stt_ms}ms</span>}
                <span className="hop">🧠 gpt-oss {last.timings.llm_ms}ms</span>
                {last.tools.map((t, i) => (
                  <motion.span key={`${t}${i}`} className="hop tool" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.12 }}>
                    ⚙️ {t}
                  </motion.span>
                ))}
                <span className="hop">🔊 {last.timings.tts_ms ? `ElevenLabs ${last.timings.tts_ms}ms` : "voice"}</span>
              </>
            ) : (
              <span className="hop muted">Hold <kbd>Space</kbd> to talk · Hinglish welcome</span>
            )}
          </div>
          {error && <div className="error">{error}</div>}
        </section>

        <section className="side">
          <div className="row">
            <Countdown deadline={deadline} offsetMs={offsetMs} />
            {view ? <LiabilityMeter view={view} /> : <div className="clay liability placeholder">RBI protection window appears here</div>}
          </div>
          <IncidentCard incident={view?.incident ?? emptyIncident} />
          {view ? (
            <ActionPlan plan={view.plan} offsetMs={offsetMs} onToggle={async (id) => apply(await api.toggleStep(view.id, id))} />
          ) : (
            <div className="clay plan placeholder">Your step-by-step recovery plan builds itself as you talk.</div>
          )}
          <motion.button
            className={`docs-btn ${draftsReady ? "ready" : ""}`}
            onClick={() => view && setDocsOpen(true)}
            disabled={!view}
            animate={draftsReady ? { scale: [1, 1.05, 1] } : {}}
            transition={{ repeat: draftsReady ? Infinity : 0, duration: 1.6 }}
          >
            📄 {draftsReady ? "Complaint drafts ready" : "Complaint drafts"}
          </motion.button>
        </section>
      </main>

      <AnimatePresence>
        {docsOpen && view && <DocsDrawer caseId={view.id} version={docsVersion} onClose={() => setDocsOpen(false)} />}
      </AnimatePresence>
    </div>
  );
}

const emptyIncident = {
  victim_name: null, amount: null, channel: null, scam_type: null, fraud_time: null, txn_ref: null,
  victim_bank: null, payment_app: null, scammer_handle: null, otp_shared: null, still_in_contact: null, summary: null,
};
