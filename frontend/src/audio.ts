/**
 * Mic capture, reply playback and a shared "voice level" the 3D mascot reads
 * every frame to move its mouth and pulse its antenna.
 */

export const voice = { level: 0 };

let ctx: AudioContext | null = null;
const audioCtx = () => (ctx ??= new AudioContext());

function meter(source: AudioNode, gain = 1): () => void {
  const analyser = audioCtx().createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);
  const buf = new Uint8Array(analyser.fftSize);
  let raf = 0;
  const tick = () => {
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (const v of buf) sum += ((v - 128) / 128) ** 2;
    const rms = Math.sqrt(sum / buf.length);
    voice.level = Math.min(1, rms * 4 * gain);
    raf = requestAnimationFrame(tick);
  };
  tick();
  return () => {
    cancelAnimationFrame(raf);
    voice.level = 0;
    analyser.disconnect();
  };
}

export class Recorder {
  private rec?: MediaRecorder;
  private chunks: Blob[] = [];
  private stopMeter?: () => void;
  private stream?: MediaStream;

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    });
    this.stopMeter = meter(audioCtx().createMediaStreamSource(this.stream));
    this.chunks = [];
    this.rec = new MediaRecorder(this.stream, { mimeType: "audio/webm;codecs=opus" });
    this.rec.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.rec.start();
  }

  stop(): Promise<Blob> {
    return new Promise((resolve) => {
      if (!this.rec) return resolve(new Blob());
      this.rec.onstop = () => {
        this.stopMeter?.();
        this.stream?.getTracks().forEach((t) => t.stop());
        resolve(new Blob(this.chunks, { type: "audio/webm" }));
      };
      this.rec.stop();
    });
  }
}

/** Play an mp3 (base64) through the analyser so the mascot lip-syncs. */
export async function playMp3(b64: string): Promise<void> {
  const ac = audioCtx();
  await ac.resume();
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const buffer = await ac.decodeAudioData(bytes.buffer);
  const src = ac.createBufferSource();
  src.buffer = buffer;
  src.connect(ac.destination);
  const stop = meter(src, 1.4);
  return new Promise((resolve) => {
    src.onended = () => {
      stop();
      resolve();
    };
    src.start();
  });
}

/** Free fallback when the ElevenLabs credit guard kicks in. */
export function speakWithBrowser(text: string): Promise<void> {
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text);
    const voices = speechSynthesis.getVoices();
    u.voice = voices.find((v) => v.lang === "hi-IN") ?? voices.find((v) => v.lang === "en-IN") ?? null;
    u.rate = 1.02;
    let raf = 0;
    const wobble = () => {
      voice.level = 0.25 + Math.abs(Math.sin(performance.now() / 90)) * 0.5;
      raf = requestAnimationFrame(wobble);
    };
    u.onstart = wobble;
    u.onend = u.onerror = () => {
      cancelAnimationFrame(raf);
      voice.level = 0;
      resolve();
    };
    speechSynthesis.speak(u);
  });
}

/** Demo/automation hook: play a pre-recorded clip into the meter as if spoken. */
export async function fakeSpeak(url: string): Promise<Blob> {
  const ac = audioCtx();
  await ac.resume();
  const blob = await fetch(url).then((r) => r.blob());
  const buffer = await ac.decodeAudioData(await blob.arrayBuffer());
  const src = ac.createBufferSource();
  src.buffer = buffer;
  const stop = meter(src, 1.2);
  await new Promise<void>((resolve) => {
    src.onended = () => resolve();
    src.start();
  });
  stop();
  return blob;
}
