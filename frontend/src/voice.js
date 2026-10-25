/* voice.js -- thin wrappers over the browser's built-in speech APIs.
 *
 * Nothing here talks to the SchemeSetu backend or costs any API quota:
 *   - voice INPUT  uses SpeechRecognition  (Chrome/Edge; sends audio to the
 *                  browser vendor's service, so it needs internet)
 *   - voice OUTPUT uses speechSynthesis    (uses voices installed on the device;
 *                  Indian-language voices vary a lot between devices)
 * Both are feature-detected so unsupported browsers degrade to a message.
 */

const Recognition =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export function voiceInputSupported() {
  return Boolean(Recognition);
}

export function voiceOutputSupported() {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

/* ------------------------------------------------------------------ */
/* Voice input                                                         */
/* ------------------------------------------------------------------ */

/* Returns a recognizer (call .start() / .stop()) or null if unsupported.
   onText(text)  -- fires as words arrive (interim + final combined)
   onError(code) -- SpeechRecognition error code, e.g. "not-allowed", "no-speech"
   onEnd(text)   -- always fires once at the end with the final transcript */
export function createRecognizer({ lang, onText, onError, onEnd }) {
  if (!Recognition) return null;
  const rec = new Recognition();
  rec.lang = lang;
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;

  let finalText = "";
  rec.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) finalText += result[0].transcript;
      else interim += result[0].transcript;
    }
    onText((finalText + interim).trim());
  };
  rec.onerror = (event) => onError(event.error);
  rec.onend = () => onEnd(finalText.trim());
  return rec;
}

/* ------------------------------------------------------------------ */
/* Script check: did the recognizer return the script we asked for?    */
/* ------------------------------------------------------------------ */

const SCRIPT_RANGES = [
  ["devanagari", 0x0900, 0x097f],
  ["bengali", 0x0980, 0x09ff],
  ["gurmukhi", 0x0a00, 0x0a7f],
  ["gujarati", 0x0a80, 0x0aff],
  ["tamil", 0x0b80, 0x0bff],
  ["telugu", 0x0c00, 0x0c7f],
  ["kannada", 0x0c80, 0x0cff],
  ["malayalam", 0x0d00, 0x0d7f],
  ["arabic", 0x0600, 0x06ff], // e.g. Punjabi returned in Shahmukhi instead of Gurmukhi
];

export const EXPECTED_SCRIPT = {
  en: "latin", hi: "devanagari", mr: "devanagari", ta: "tamil", te: "telugu",
  kn: "kannada", ml: "malayalam", bn: "bengali", gu: "gujarati", pa: "gurmukhi",
};

/* Dominant script of `text` ("latin", "tamil", ...) or null if it has no letters. */
export function scriptOf(text) {
  const counts = {};
  for (const ch of String(text || "")) {
    const cp = ch.codePointAt(0);
    let script = null;
    if ((cp >= 0x41 && cp <= 0x5a) || (cp >= 0x61 && cp <= 0x7a)) script = "latin";
    else {
      const hit = SCRIPT_RANGES.find(([, lo, hi]) => cp >= lo && cp <= hi);
      if (hit) script = hit[0];
    }
    if (script) counts[script] = (counts[script] || 0) + 1;
  }
  let best = null;
  for (const [script, n] of Object.entries(counts)) {
    if (!best || n > counts[best]) best = script;
  }
  return best;
}

/* True when a transcript of 3+ words is mostly in a different script from the
   language the mic was set to. Soft signal only: Latin text in an Indian-language
   chat can be legitimate (English words like PM-KISAN), so it just triggers a hint. */
export function transcriptScriptMismatch(text, langCode) {
  const expected = EXPECTED_SCRIPT[langCode];
  if (!expected || langCode === "en") return false;
  const words = String(text || "").trim().split(/\s+/).filter(Boolean);
  if (words.length < 3) return false;
  const detected = scriptOf(text);
  return detected !== null && detected !== expected;
}

/* ------------------------------------------------------------------ */
/* Voice output                                                        */
/* ------------------------------------------------------------------ */

/* Answers are markdown; reading "asterisk asterisk" aloud is awful. */
export function stripMarkdown(text) {
  return String(text || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+[.)]\s+/gm, "")
    .replace(/(\*\*|__|\*|_)/g, "")
    .replace(/^\s*>\s?/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

/* Chrome silently stops reading long utterances after ~15 seconds, so speak
   in sentence-sized pieces. Splits on . ! ? and the Devanagari/Bengali/Gurmukhi
   danda (।) and keeps each piece under `max` characters. */
export function splitIntoChunks(text, max = 180) {
  const sentences = text.match(/[^.!?।॥]+[.!?।॥]*/g) || [text];
  const chunks = [];
  let current = "";
  for (const raw of sentences) {
    const sentence = raw.trim();
    if (!sentence) continue;
    if ((current + " " + sentence).trim().length <= max) {
      current = (current + " " + sentence).trim();
      continue;
    }
    if (current) chunks.push(current);
    if (sentence.length <= max) {
      current = sentence;
    } else {
      // one very long sentence: break at spaces
      let rest = sentence;
      while (rest.length > max) {
        let cut = rest.lastIndexOf(" ", max);
        if (cut < max / 2) cut = max;
        chunks.push(rest.slice(0, cut).trim());
        rest = rest.slice(cut).trim();
      }
      current = rest;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

function allVoices() {
  return voiceOutputSupported() ? window.speechSynthesis.getVoices() : [];
}

function pickVoice(speechLang) {
  const voices = allVoices();
  const wanted = speechLang.toLowerCase();
  const base = wanted.split("-")[0];
  return (
    voices.find((v) => v.lang.toLowerCase().replace("_", "-") === wanted) ||
    voices.find((v) => v.lang.toLowerCase().startsWith(base)) ||
    null
  );
}

/* True if the device has any voice for this language. Voices load
   asynchronously in Chrome, so an empty list means "unknown yet", which we
   treat as available rather than nagging the user. */
export function hasVoiceFor(speechLang) {
  if (!voiceOutputSupported()) return false;
  if (allVoices().length === 0) return true;
  return pickVoice(speechLang) !== null;
}

let activeToken = 0;

export function stopSpeaking() {
  activeToken += 1; // makes any in-flight callbacks stale
  if (voiceOutputSupported()) window.speechSynthesis.cancel();
}

/* Read `text` aloud. onEnd fires once when finished OR if speech fails;
   it does NOT fire when stopSpeaking() cancels it (the caller already knows). */
export function speak(text, speechLang, { onEnd } = {}) {
  if (!voiceOutputSupported()) {
    if (onEnd) onEnd();
    return;
  }
  const chunks = splitIntoChunks(stripMarkdown(text));
  if (chunks.length === 0) {
    if (onEnd) onEnd();
    return;
  }

  window.speechSynthesis.cancel();
  const token = ++activeToken;
  const voice = pickVoice(speechLang);
  let finished = 0;

  const done = () => {
    if (token !== activeToken) return;
    if (onEnd) onEnd();
  };

  chunks.forEach((chunk) => {
    const utterance = new window.SpeechSynthesisUtterance(chunk);
    utterance.lang = speechLang;
    if (voice) utterance.voice = voice;
    utterance.rate = 0.95;
    utterance.onend = () => {
      finished += 1;
      if (finished === chunks.length) done();
    };
    utterance.onerror = () => {
      if (token !== activeToken) return; // cancelled on purpose
      activeToken += 1;
      window.speechSynthesis.cancel();
      if (onEnd) onEnd();
    };
    window.speechSynthesis.speak(utterance);
  });
}
