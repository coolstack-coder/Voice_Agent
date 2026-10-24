import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import type { CaseView, Incident, Step } from "../api";

const SCAM_LABEL: Record<string, string> = {
  digital_arrest: "Digital arrest",
  kyc_update: "Fake KYC",
  fake_customer_care: "Fake customer care",
  investment_task: "Task / investment",
  otp_share: "OTP trick",
  remote_app: "Screen-share app",
  sextortion: "Sextortion",
  upi_collect: "UPI collect request",
  other: "Online fraud",
};

export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
const fmtDay = (iso: string) =>
  new Date(iso).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });

export function Countdown({ deadline, offsetMs }: { deadline: string | null; offsetMs: number }) {
  const now = useNow() + offsetMs;
  if (!deadline) {
    return (
      <div className="clay countdown waiting">
        <div className="eyebrow">Golden hour</div>
        <div className="digits muted">--:--</div>
        <div className="hint">Starts when you tell me <b>when</b> the money left.</div>
      </div>
    );
  }
  const left = Math.max(0, new Date(deadline).getTime() - now);
  const m = Math.floor(left / 60000);
  const s = Math.floor((left % 60000) / 1000);
  const urgent = left < 15 * 60000;
  return (
    <motion.div className={`clay countdown ${urgent ? "urgent" : ""}`} layout>
      <div className="eyebrow">Golden hour left</div>
      <div className="digits">
        {String(m).padStart(2, "0")}
        <span className="colon">:</span>
        {String(s).padStart(2, "0")}
      </div>
      <div className="hint">
        {left === 0 ? "Golden hour passed. Still report: holds still happen." : `Freeze window closes at ${fmtTime(deadline)}`}
      </div>
    </motion.div>
  );
}

type Field = { key: keyof Incident; label: string; render?: (v: any) => string };
const FIELDS: Field[] = [
  { key: "amount", label: "Amount", render: (v) => `₹${Number(v).toLocaleString("en-IN")}` },
  { key: "scam_type", label: "Scam type", render: (v) => SCAM_LABEL[v] ?? v },
  { key: "fraud_time", label: "When", render: (v) => fmtTime(v) },
  { key: "channel", label: "Paid via", render: (v) => String(v).toUpperCase() },
  { key: "payment_app", label: "App" },
  { key: "victim_bank", label: "Bank" },
  { key: "txn_ref", label: "UTR" },
  { key: "scammer_handle", label: "Scammer id" },
];

export function IncidentCard({ incident }: { incident: Incident }) {
  return (
    <div className="clay incident">
      <div className="card-head">
        <span className="badge">Case file</span>
        {incident.still_in_contact && <span className="pill danger">Still on call!</span>}
        {incident.otp_shared && <span className="pill warn">OTP shared</span>}
      </div>
      <div className="fields">
        {FIELDS.map((f) => {
          const v = incident[f.key];
          const has = v !== null && v !== undefined && v !== "";
          return (
            <div key={f.key} className={`field ${has ? "filled" : ""}`}>
              <div className="flabel">{f.label}</div>
              <AnimatePresence mode="wait">
                {has ? (
                  <motion.div
                    key={String(v)}
                    className="fval"
                    initial={{ scale: 1.8, opacity: 0, rotate: -8 }}
                    animate={{ scale: 1, opacity: 1, rotate: 0 }}
                    transition={{ type: "spring", stiffness: 380, damping: 16 }}
                  >
                    {f.render ? f.render(v) : String(v)}
                  </motion.div>
                ) : (
                  <motion.div key="empty" className="fval empty">?</motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ActionPlan({ plan, onToggle, offsetMs }: { plan: Step[]; onToggle: (id: string) => void; offsetMs: number }) {
  const now = useNow(15000) + offsetMs;
  return (
    <div className="clay plan">
      <div className="card-head">
        <span className="badge">Recovery plan</span>
        <span className="sub">{plan.filter((s) => s.done).length}/{plan.length} done</span>
      </div>
      <motion.ol layout className="steps">
        <AnimatePresence initial={false}>
          {plan.map((s, i) => {
            const overdue = s.deadline && !s.done && new Date(s.deadline).getTime() < now;
            return (
              <motion.li
                layout
                key={s.id}
                className={`step ${s.done ? "done" : ""} ${i === 0 && !s.done ? "top" : ""}`}
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 26 }}
              >
                <button className="tick" onClick={() => onToggle(s.id)} aria-label={`toggle ${s.title}`}>
                  {s.done ? "✓" : i + 1}
                </button>
                <div className="step-body">
                  <div className="step-title">
                    {s.action ? <a href={s.action} target="_blank" rel="noreferrer">{s.title}</a> : s.title}
                  </div>
                  <div className="step-why">{s.why}</div>
                </div>
                {s.deadline && (
                  <div className={`deadline ${overdue ? "late" : ""}`}>
                    <div>{s.tags.includes("rbi") ? fmtDay(s.deadline) : fmtTime(s.deadline)}</div>
                    <small>{s.tags.includes("rbi") ? "RBI 3 working days" : s.tags.includes("golden-hour") ? "golden hour" : "deadline"}</small>
                  </div>
                )}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </motion.ol>
    </div>
  );
}

const BANDS = [
  { id: "zero", label: "Zero liability" },
  { id: "capped", label: "Capped" },
  { id: "bank_policy", label: "Bank policy" },
];

export function LiabilityMeter({ view }: { view: CaseView }) {
  const l = view.liability;
  const idx = l.band === "negligence" ? 2 : BANDS.findIndex((b) => b.id === l.band);
  return (
    <div className="clay liability">
      <div className="card-head">
        <span className="badge">RBI protection</span>
        {l.zero_by && <span className="sub">report by {fmtDay(l.zero_by)}</span>}
      </div>
      <div className="meter">
        {BANDS.map((b, i) => (
          <div key={b.id} className={`band b${i} ${i === idx ? "on" : ""}`}>{b.label}</div>
        ))}
      </div>
      <p className="lnote">{l.text}</p>
    </div>
  );
}
