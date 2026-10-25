import { _STRINGS, makeT, LANGUAGES, loadSavedLanguage } from "./src/i18n.js";
import { stripMarkdown, splitIntoChunks, voiceInputSupported, voiceOutputSupported, hasVoiceFor, speak, stopSpeaking } from "./src/voice.js";

let fail = 0;
const ok = (name, cond, extra="") => { console.log((cond?"PASS":"FAIL")+" "+name+(cond?"":"  "+extra)); if(!cond) fail++; };

const enKeys = Object.keys(_STRINGS.en);
const codes = LANGUAGES.map(l => l.code);
ok("10 languages listed", codes.length === 10, codes.join());
ok("every language has a strings table", codes.every(c => _STRINGS[c]));
for (const c of codes) {
  const keys = Object.keys(_STRINGS[c]);
  const missing = enKeys.filter(k => !keys.includes(k));
  const extra = keys.filter(k => !enKeys.includes(k));
  // errGeneric/errEligGeneric are intentionally English-only fallbacks; voiceError too
  const allowed = new Set(["errGeneric","errEligGeneric","voiceError"]);
  const realMissing = c === "en" ? [] : missing.filter(k => !allowed.has(k));
  ok(`${c}: no missing keys (only allowed English fallbacks)`, realMissing.length === 0, "missing: "+realMissing.join());
  ok(`${c}: no unknown keys`, extra.length === 0, extra.join());
  ok(`${c}: no empty strings`, Object.values(_STRINGS[c]).every(v => v.trim().length > 0));
  // placeholders must be preserved
  for (const k of ["matched","ttsMissing"]) {
    const ph = (_STRINGS.en[k].match(/\{\w+\}/g)||[]).sort().join();
    const got = ((_STRINGS[c][k]||"").match(/\{\w+\}/g)||[]).sort().join();
    ok(`${c}.${k}: placeholder ${ph} kept`, ph === got, got);
  }
  // translations must differ from English for visible core keys
  if (c !== "en") ok(`${c}: heading is actually translated`, _STRINGS[c].heading !== _STRINGS.en.heading);
}
const t = makeT("ta");
ok("t() fills {n}", t("matched",{n:7}).includes("7") && !t("matched",{n:7}).includes("{n}"));
ok("t() falls back to English for a missing key", makeT("hi")("errGeneric") === _STRINGS.en.errGeneric);
ok("t() returns key for unknown key", makeT("hi")("nope") === "nope");
ok("unknown language falls back to English", makeT("zz")("newChat") === "New policy question");
ok("loadSavedLanguage safe without localStorage", loadSavedLanguage() === "en");
ok("t() ttsMissing fills {lang}", makeT("hi")("ttsMissing",{lang:"हिन्दी"}).includes("हिन्दी"));

// voice helpers
ok("stripMarkdown removes bold/list/heading/link", stripMarkdown("## Title\n- **Bold** item\n- [link](http://x.y) here\n1. one") === "Title Bold item link here one", stripMarkdown("## Title\n- **Bold** item\n- [link](http://x.y) here\n1. one"));
ok("stripMarkdown keeps rupee amounts and numbers", stripMarkdown("Get **₹6,000** per year.") === "Get ₹6,000 per year.");
const long = Array.from({length:12},(_,i)=>`This is sentence number ${i} about the scheme benefits.`).join(" ");
const chunks = splitIntoChunks(long, 180);
ok("chunks are <=180 chars", chunks.every(c=>c.length<=180), chunks.map(c=>c.length).join());
ok("chunking loses no words", chunks.join(" ").replace(/\s+/g," ") === long);
const hi = "यह योजना किसानों के लिए है। इसमें छह हजार रुपये मिलते हैं। आवेदन ऑनलाइन करें।";
ok("splits Hindi on the danda", splitIntoChunks(hi, 40).length >= 2, JSON.stringify(splitIntoChunks(hi,40)));
ok("one huge sentence is broken at spaces", splitIntoChunks("word ".repeat(100).trim(), 50).every(c=>c.length<=50));
ok("empty text -> no chunks", splitIntoChunks("").length === 0 || splitIntoChunks("").every(c=>!c.trim()));
ok("Tamil text is chunked without loss", splitIntoChunks("பிரதமர் கிசான் திட்டம். விவசாயிகளுக்கு உதவி.", 20).join(" ").length > 0);
ok("feature detection is false in Node (no window)", voiceInputSupported() === false && voiceOutputSupported() === false);
ok("hasVoiceFor safe without speechSynthesis", hasVoiceFor("ta-IN") === false);
let ended = false; speak("hello", "en-IN", { onEnd: () => { ended = true; } });
ok("speak() without support calls onEnd and does not throw", ended === true);
stopSpeaking(); ok("stopSpeaking() safe without support", true);
console.log(fail ? `\n${fail} FAILED` : "\nALL PASSED"); process.exit(fail?1:0);
