export type Step = {
  id: string;
  title: string;
  why: string;
  priority: number;
  deadline: string | null;
  action: string | null;
  done: boolean;
  tags: string[];
};

export type Incident = {
  victim_name: string | null;
  amount: number | null;
  channel: string | null;
  scam_type: string | null;
  fraud_time: string | null;
  txn_ref: string | null;
  victim_bank: string | null;
  payment_app: string | null;
  scammer_handle: string | null;
  otp_shared: boolean | null;
  still_in_contact: boolean | null;
  summary: string | null;
};

export type Liability = { band: string; text: string; zero_by?: string; capped_by?: string };

export type TranscriptTurn = { role: "user" | "agent"; text: string; at: string; tools: string[] };

export type CaseView = {
  id: string;
  incident: Incident;
  plan: Step[];
  golden_hour_deadline: string | null;
  liability: Liability;
  missing: string[];
  transcript: TranscriptTurn[];
  server_now: string;
};

export type TurnResult = {
  heard: string;
  reply: string;
  tools: string[];
  audio: string | null;
  timings: Record<string, number>;
  case: CaseView;
  tts_credits_left: number;
};

export type Health = { ok: boolean; tts: string; tts_credits_left: number; llm: string; stt: string };

export type Documents = {
  ncrp: { title: string; fields: { label: string; value: string }[] };
  bank_letter: { title: string; body: string };
  missing: string[];
};

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => fetch("/api/health").then(j<Health>),
  createCase: () => fetch("/api/cases", { method: "POST" }).then(j<CaseView>),
  getCase: (id: string) => fetch(`/api/cases/${id}`).then(j<CaseView>),
  toggleStep: (id: string, step: string) =>
    fetch(`/api/cases/${id}/steps/${step}`, { method: "POST" }).then(j<CaseView>),
  documents: (id: string) => fetch(`/api/cases/${id}/documents`).then(j<Documents>),
  turn: (id: string, input: Blob | string) => {
    const form = new FormData();
    if (typeof input === "string") form.append("text", input);
    else form.append("audio", input, input.type.includes("wav") ? "speech.wav" : "speech.webm");
    return fetch(`/api/cases/${id}/turn`, { method: "POST", body: form }).then(j<TurnResult>);
  },
};
