# Problem research: why GoldenHour

Before writing any code I spent the first block of time on **problem discovery**:
five parallel research tracks, each with a different lens, each asked to bring back
three voice-agent ideas with evidence, a novelty check and scores.

| Lens | Ideas explored |
|---|---|
| Bharat / field workers | Crop-loss claim agent (PMFBY 72h window), garage job-card agent, wage-theft diary |
| Accessibility / caregiving | Care-shift handoff log, aphasia word-finding partner, blind-cook kitchen copilot |
| Hands-busy professionals | Circuit-debugging probe buddy, HACCP kitchen temperature logger, wet-lab protocol runner |
| Civic / safety / money | **Post-scam first responder**, scam "sparring" simulator, refund-rights claims agent |
| Character-driven help | Kid fever-dose co-pilot, autism meltdown ABC logger, household chore mediator |

Ideas rejected up front because they are already everywhere: appointment booking,
support bots, interview practice, language tutors, kirana/udhaar voice ledgers
(Vyapar Saathi, Dukaan Saathi, VoiceKhata…), real-time scam-call detectors.

## Scoring (1–10)

| Idea | Pain | Novelty | Browser demo | LinkedIn | Buildable |
|---|---|---|---|---|---|
| **GoldenHour – post-scam first responder** | 9 | 8 | 9 | 9 | 8 |
| ShiftNote – caregiver handoff | 9 | 8 | 9 | 9 | 8 |
| TipWord – aphasia word finder | 9 | 9 | 8 | 10 | 7 (STT risk on aphasic speech) |
| Nuksaan – crop-loss claim | 9 | 7 | 9 | 8 | 8 |
| Mistri – garage job card | 7 | 8 | 9 | 8 | 8 |
| Dosey – fever-dose co-pilot | 9 | 8 | 9 | 9 | 8 (medical liability) |

## The problem

* India loses **₹22,000+ crore a year** to cyber fraud
  ([Moneylife](https://moneylife.in/article/fraud-alert-india-is-losing-over-22000-crore-a-year-in-cyber-scams-and-the-worst-is-yet-to-come/80612.html)).
* "Digital arrest" cases went from ~40k (2022) to ~1.24 lakh (2024)
  ([The Wire](https://thewire.in/tech/indians-lost-nearly-rs-2000-crore-to-digital-arrest-scams-in-2024-report)).
* Money can only be frozen if it is reported in the **golden hour** – before it is
  layered across mule accounts. Mumbai's 1930 helpline alone saved ₹241 crore this way
  ([Deccan Herald](https://www.deccanherald.com/india/maharashtra/mumbai-fights-back-complaints-on-cyber-crime-helpline-1930-touches-1-lakh-mark-rs-241-cr-saved-3491941)).
  Delays of 3–15 days make recovery "very difficult"
  ([Free Press Journal](https://www.freepressjournal.in/mumbai/digital-arrest-is-not-real-call-1930-if-you-fall-victim-to-cyber-fraud-cm-fadnavis)).
* RBI's 2017 circular gives **zero liability** for third-party fraud only if the bank is
  told within **3 working days**; 4–7 days = capped liability; and if credentials (OTP)
  were shared the customer bears the loss *until they report it*
  ([RBI](https://rbi.org.in/Scripts/NotificationUser.aspx?Id=11040)).

The victim, in the worst 15 minutes of their month, is expected to remember UTR numbers,
find the right helpline, fill a portal form, call the bank and count working days.
They are shaking. They ramble. They mix Hindi and English.

## Why voice is essential (not a gimmick)

Panic destroys fine motor control and reading comprehension. Talking is the one channel
that still works. GoldenHour lets the victim *vent*, and turns the rambling into a
structured case, a live countdown, a prioritised action plan and ready-to-file drafts.

## Novelty check

Searches found static "how to report" guides and crowded *scam-call detection* projects,
but no agent that works the **minutes after** the fraud: extraction → deadline engine →
checklist → complaint packet.

## Safety stance

GoldenHour is procedural first aid, not legal advice. Deadlines and documents come from
a deterministic rules engine and templates – the LLM never invents a helpline, a law
or a number. Sensitive digits (OTP, card, Aadhaar) are masked before storage.
