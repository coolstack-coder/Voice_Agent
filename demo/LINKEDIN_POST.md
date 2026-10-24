Someone you know will get this call.

"I'm a CBI officer. A drugs parcel was seized in your name. Transfer the money now or you'll be arrested."

India loses ₹22,000+ crore a year to cyber fraud, and "digital arrest" cases tripled in two years. Recovery comes down to one thing: speed. If the fraud is reported on 1930 within the golden hour, banks can freeze the money before it moves through mule accounts. Wait three days and it's mostly gone.

But in those first minutes the victim is shaking. They can't find the UTR, they don't know which portal to use, and they're definitely not counting RBI working days.

So I built GoldenHour 🛡️, a voice agent for the first 60 minutes after a scam.

You hold one button and talk, in Hindi, English or Hinglish, as messily as panic makes you. Kavach, a calm 3D cartoon guardian, listens and turns the rambling into:
⏱️ a live golden-hour countdown, worked out from "20 minute pehle"
📋 a case file: amount, scam type, UTR, bank, the scammer's number
✅ a recovery plan with real deadlines that ticks itself off as you say "1930 pe call kar diya"
🏦 your RBI zero-liability window (it skips Sundays and 2nd/4th Saturdays, the way banks count)
🧾 ready-to-file drafts for cybercrime.gov.in and a bank dispute letter

What I learned building it:
→ The LLM extracts, the code decides. gpt-oss-120b (on Groq) only gets two tools. Deadlines, helplines and documents all come from deterministic Python, so it can't invent a law or a phone number.
→ The model never does date math. It says "15 minutes ago"; the code does the arithmetic.
→ A UTR and an Aadhaar number are both 12 digits. One is evidence and one is a secret, so redaction looks at the words around the number.
→ Every failure I hit in end-to-end testing (a wrong step ticked, an empty reply, a number where text was expected) became a guardrail with a unit test.
→ I had a strict ElevenLabs credit budget, so TTS reads the real cost from the API header, caches every phrase and falls back to the browser's voice.

Stack: Groq Whisper (STT) · gpt-oss-120b tool calling · ElevenLabs Flash (TTS) · FastAPI · React + three.js

Before writing any code I spent the first block of time on problem discovery: five research tracks and fifteen voice-agent ideas, scored for pain and novelty. Scam *detectors* are everywhere. Almost nobody is building for the minutes *after* the scam.

The 6-minute demo walks through a real run and the codebase 👇
Code: github.com/coolstack-coder/Voice_Agent

And if you remember one thing from this post, remember 1930.

#VoiceAI #AIAgents #CyberSecurity #Groq #ElevenLabs #BuildInPublic #India #FastAPI #ThreeJS #LLM
