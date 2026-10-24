import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api, type Documents } from "../api";

export function DocsDrawer({ caseId, version, onClose }: { caseId: string; version: number; onClose: () => void }) {
  const [docs, setDocs] = useState<Documents | null>(null);
  const [tab, setTab] = useState<"ncrp" | "letter">("ncrp");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.documents(caseId).then(setDocs);
  }, [caseId, version]);

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  const download = (name: string, text: string) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = name;
    a.click();
  };

  const ncrpText = docs?.ncrp.fields.map((f) => `${f.label}: ${f.value}`).join("\n") ?? "";

  return (
    <motion.div className="drawer-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.aside
        className="drawer clay"
        initial={{ x: 80, opacity: 0, rotate: 2 }}
        animate={{ x: 0, opacity: 1, rotate: 0 }}
        exit={{ x: 80, opacity: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 24 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drawer-head">
          <h2>Ready-to-file drafts</h2>
          <button className="ghost" onClick={onClose}>✕</button>
        </div>
        {docs && docs.missing.length > 0 && (
          <div className="missing">Still needed: {docs.missing.map((m) => m.replace("_", " ")).join(", ")}</div>
        )}
        <div className="tabs">
          <button className={tab === "ncrp" ? "on" : ""} onClick={() => setTab("ncrp")}>cybercrime.gov.in form</button>
          <button className={tab === "letter" ? "on" : ""} onClick={() => setTab("letter")}>Bank dispute letter</button>
        </div>
        {docs && tab === "ncrp" && (
          <div className="doc">
            {docs.ncrp.fields.map((f) => (
              <div key={f.label} className="docrow">
                <span>{f.label}</span>
                <b className={f.value.startsWith("[MISSING") ? "miss" : ""}>{f.value}</b>
              </div>
            ))}
            <div className="doc-actions">
              <button onClick={() => copy(ncrpText)}>{copied ? "Copied!" : "Copy all fields"}</button>
              <a className="btn" href="https://cybercrime.gov.in" target="_blank" rel="noreferrer">Open portal ↗</a>
            </div>
          </div>
        )}
        {docs && tab === "letter" && (
          <div className="doc">
            <pre className="letter">{docs.bank_letter.body}</pre>
            <div className="doc-actions">
              <button onClick={() => copy(docs.bank_letter.body)}>{copied ? "Copied!" : "Copy letter"}</button>
              <button onClick={() => download("bank-dispute-letter.txt", docs.bank_letter.body)}>Download</button>
            </div>
          </div>
        )}
      </motion.aside>
    </motion.div>
  );
}
