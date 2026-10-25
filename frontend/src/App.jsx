import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import AdminPage from "./AdminPage";
import {
  Menu,
  X,
  Plus,
  Send,
  FileText,
  Sprout,
  GraduationCap,
  Users,
  Home as HomeIcon,
  HeartPulse,
  RotateCcw,
  ArrowUpRight,
  BookOpenCheck,
  LibraryBig,
  ClipboardCheck,
  Filter,
  Landmark,
  MapPin,
  Mic,
  ChevronDown,
  ChevronUp,
  Square,
  Volume2,
  Languages as LanguagesIcon,
  Sun,
  Moon,
  ArrowLeftRight,
  FileDown,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { LANGUAGES, languageInfo, loadSavedLanguage, makeT, saveLanguage } from "./i18n";
import {
  createRecognizer,
  hasVoiceFor,
  speak,
  stopSpeaking,
  transcriptScriptMismatch,
  voiceInputSupported,
  voiceOutputSupported,
} from "./voice";
import { DocumentPlanner, EventChips, VerdictBlock, VerifyBar } from "./Planner";
import { pt } from "./planner_strings";
import { applyTheme, getInitialTheme } from "./theme";
import { tEvent } from "./i18n_extra";
import { API_BASE } from "./config";
import "./chat-history.css";

// Chat history is kept in this browser (localStorage). No account or backend needed.
const HISTORY_KEY = "schemesetu_chat_history_v1";
const MAX_SAVED_CHATS = 30;

function newThreadId() {
  return `t_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function loadThreads() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function persistThreads(list) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, MAX_SAVED_CHATS)));
  } catch {
    // storage full or blocked: history just won't survive a refresh
  }
}

const ELIGIBILITY_URL = `${API_BASE}/eligibility`;
const ELIGIBILITY_OPTIONS_URL = `${API_BASE}/eligibility/options`;

const API_URL = `${API_BASE}/ask`;
const TRANSLATE_URL = `${API_BASE}/translate`;
const TRANSLATE_BATCH_URL = `${API_BASE}/translate/batch`;
const SCHEMES_INFO_URL = `${API_BASE}/schemes/info`;
const MAX_HISTORY_TURNS = 3; // keep in sync with MAX_HISTORY_TURNS in rag_chat.py

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>\"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
  }[ch]));
}

function exportChecklist(schemes, title, t) {
  if (!schemes.length) return;
  const rows = schemes.map((scheme) => {
    const docs = (scheme.documents_needed || []).map((d) => typeof d === "string" ? d : d.label).filter(Boolean);
    const applyUrl = scheme.apply_url || (scheme.slug ? `https://www.myscheme.gov.in/schemes/${scheme.slug}` : "");
    return `<article class="scheme"><h2>□ ${escapeHtml(scheme.scheme_name)}</h2>
      <p class="meta">${escapeHtml([scheme.level, scheme.state, scheme.category].filter(Boolean).join(" · "))}</p>
      <p><strong>${escapeHtml(pt(t, "comparisonEligibility"))}</strong><br>${escapeHtml(scheme.eligibility_snippet || pt(t, "schemeDocumentsUnknown"))}</p>
      ${scheme.benefits_snippet ? `<p><strong>${escapeHtml(pt(t, "comparisonBenefits"))}</strong><br>${escapeHtml(scheme.benefits_snippet)}</p>` : ""}
      <p><strong>${escapeHtml(pt(t, "schemeDocuments"))}</strong><br>${docs.length ? docs.map(escapeHtml).join(" · ") : escapeHtml(scheme.documents_note || pt(t, "schemeDocumentsUnknown"))}</p>
      ${applyUrl ? `<p><a href="${escapeHtml(applyUrl)}">${escapeHtml(pt(t, "officialApply"))}</a></p>` : ""}
      <p class="notes">${escapeHtml(pt(t, "checklistNotes"))}: ______________________________________________________________</p></article>`;
  }).join("");
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    window.alert(pt(t, "allowPopups"));
    return;
  }
  printWindow.document.write(`<!doctype html><html lang="${escapeHtml(t.language || "en")}"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
    <style>body{font:14px Arial,sans-serif;color:#17233d;margin:28px auto;max-width:780px;padding:0 24px}h1{font-size:24px;margin-bottom:4px}.date,.meta{color:#687080;font-size:12px}.scheme{border:1px solid #d9d4c9;border-radius:8px;padding:14px 18px;margin:18px 0;break-inside:avoid}.scheme h2{font-size:17px;margin:0}.scheme p{line-height:1.5}.notes{margin-top:22px;color:#687080}a{color:#234c83}@page{size:A4;margin:16mm}@media print{body{margin:0;max-width:none;padding:0}.scheme{break-inside:avoid}}</style></head><body>
    <h1>${escapeHtml(title)}</h1><p class="date">SchemeSetu · ${new Date().toLocaleDateString(languageInfo(t.language).speech)}</p>${rows}
    <script>window.onload=()=>{window.focus();window.print()}</script></body></html>`);
  printWindow.document.close();
}

/* Turn the flat question/answer message list into the last few
   {question, answer} pairs the backend expects, so follow-ups like
   "what documents do I need for that?" can resolve against them. */
function buildHistory(messages) {
  const turns = [];
  for (let i = 0; i < messages.length; i++) {
    if (messages[i].role !== "question") continue;
    const next = messages[i + 1];
    if (next && next.role === "answer") {
      // Non-English chats: send the English translation the server returned, so
      // scheme-name matching for follow-ups ("what documents for that?") still works.
      turns.push({ question: messages[i].englishQuestion || messages[i].text, answer: next.text });
    }
  }
  return turns.slice(-MAX_HISTORY_TURNS);
}

/* Turn a failed fetch into a message a citizen can act on. `response` is the
   fetch Response (or null if the request never reached the server). */
async function describeFailure(response, fallback, t) {
  if (!response) return t("errOffline");
  if (response.status === 429) return t("errQuota");
  if (response.status === 503) return t("errUnavailable");
  if (response.status === 400 || response.status === 401 || response.status === 422) {
    const body = await response.json().catch(() => ({}));
    if (typeof body.detail === "string") return body.detail;
  }
  return fallback;
}

const CATEGORIES = [
  { labelKey: "catFarmers", icon: Sprout, query: "What schemes are available for farmers?" },
  { labelKey: "catStudents", icon: GraduationCap, query: "What schemes are available for students?" },
  { labelKey: "catWomen", icon: Users, query: "What schemes are available for women?" },
  { labelKey: "catHousing", icon: HomeIcon, query: "What housing schemes are available?" },
  { labelKey: "catHealthcare", icon: HeartPulse, query: "What healthcare schemes are available?" },
];

const SUGGESTIONS = [
  "What are the eligibility criteria for Pradhan Mantri Kisan Samman Nidhi?",
  "What documents do I need for PM-KISAN?",
  "What schemes are available for farmers?",
  "What are the benefits of Namo Shetkari Mahasanman Nidhi Yojana?",
  "What schemes are available for women?",
];

const QUICK_TEMPLATES = [
  { id: "Elig", label: "Eligibility", text: "What is the eligibility criteria for " },
  { id: "Benefits", label: "Benefits", text: "What are the benefits of " },
  { id: "Docs", label: "Documents", text: "What documents are required for " },
  { id: "Apply", label: "Application process", text: "How do I apply for " },
];

const LOADING_STAGE_KEYS = ["ls1", "ls2", "ls3"];

/* ---------------------------------------------------------------- */
/* Brand mark: two nodes bridged -- "Setu" (bridge) connecting a     */
/* person-node to a document-node. No flag, no generic sparkle icon.*/
/* ---------------------------------------------------------------- */
function Logo({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path
        d="M4 22c4-8 20-8 24 0"
        stroke="var(--color-heading)"
        strokeWidth="2.2"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="4" cy="23" r="3.4" fill="var(--color-saffron)" />
      <circle cx="28" cy="23" r="3.4" fill="var(--color-heading)" />
      <circle cx="16" cy="10" r="2.6" fill="var(--color-green)" />
      <path d="M6.5 21 15 11.5M25.5 21 17 11.5" stroke="var(--color-line-strong)" strokeWidth="1.4" />
    </svg>
  );
}

function StatusDot({ status }) {
  const color =
    status === "connected" ? "var(--color-green)" : status === "checking" ? "var(--color-ink-soft)" : "#B5453F";
  return <span className="status-dot" style={{ background: color }} />;
}

/* Faint node-network texture behind the landing hero. Decorative only. */
function NetworkBackdrop() {
  return (
    <svg className="network-backdrop" viewBox="0 0 600 400" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g stroke="var(--color-heading)" strokeWidth="0.6" opacity="0.14">
        <line x1="40" y1="60" x2="180" y2="140" />
        <line x1="180" y1="140" x2="120" y2="260" />
        <line x1="180" y1="140" x2="340" y2="100" />
        <line x1="340" y1="100" x2="480" y2="180" />
        <line x1="340" y1="100" x2="300" y2="260" />
        <line x1="480" y1="180" x2="560" y2="90" />
        <line x1="120" y1="260" x2="260" y2="340" />
        <line x1="300" y1="260" x2="260" y2="340" />
        <line x1="300" y1="260" x2="440" y2="320" />
      </g>
      <g fill="var(--color-heading)" opacity="0.22">
        <circle cx="40" cy="60" r="3" />
        <circle cx="180" cy="140" r="4" />
        <circle cx="120" cy="260" r="3" />
        <circle cx="340" cy="100" r="4" />
        <circle cx="480" cy="180" r="3" />
        <circle cx="300" cy="260" r="3" />
        <circle cx="560" cy="90" r="3" />
        <circle cx="260" cy="340" r="3" />
        <circle cx="440" cy="320" r="3" />
      </g>
    </svg>
  );
}

function SourceCard({ label, info, updated, t, lang }) {
  // label already comes formatted as "Scheme Name (page N/A)" from the API.
  const match = label.match(/^(.*)\s\(page (.*)\)$/i);
  const name = match ? match[1] : label;
  const page = match ? match[2] : null;
  let asOf = null;
  if (updated) {
    const d = new Date(updated);
    if (!Number.isNaN(d.getTime())) asOf = d.toLocaleDateString(lang ? languageInfo(lang).speech : undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  return (
    <div className="source-card">
      <FileText size={15} className="source-card__icon" />
      <div className="source-card__text">
        <span className="source-card__name">{name}</span>
        <span className="source-card__meta">
          {pt(t, "srcRecord")}{page && page !== "N/A" ? ` · ${pt(t, "srcPage")} ${page}` : ""}
          {asOf ? ` · ${pt(t, "srcDataAsOf", { date: asOf })}` : ""}
        </span>
        {info && info.url && (
          <a
            className="source-card__link"
            href={info.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: "0.8rem", fontWeight: 600, textDecoration: "underline" }}
          >
            {pt(t, "srcOfficial")} ↗
          </a>
        )}
      </div>
    </div>
  );
}

/* Source cards for one answer. Fetches official-page links + the data date once. */
function SourceCards({ sources, t, lang }) {
  const [info, setInfo] = useState(null);
  const key = sources.join("|");
  useEffect(() => {
    let cancelled = false;
    fetch(SCHEMES_INFO_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ names: sources.slice(0, 10) }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => !cancelled && setInfo(data))
      .catch(() => {}); // cards still render without links
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return sources.map((src, j) => (
    <SourceCard key={j} label={src} info={info && info.schemes && info.schemes[src]} updated={info && info.data_updated} t={t} lang={lang} />
  ));
}

function LoadingIndicator({ t }) {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStage((s) => (s + 1) % LOADING_STAGE_KEYS.length), 900);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="loading-indicator" role="status" aria-live="polite">
      <span className="loading-indicator__pulse" />
      {t(LOADING_STAGE_KEYS[stage])}
    </div>
  );
}

function formatProfileSummary(profile, categoryLabels, t, eventLabels) {
  const parts = [];
  if (profile.event) parts.push(tEvent(t, (eventLabels && eventLabels[profile.event]) || profile.event));
  if (profile.age) parts.push(`${t("age")} ${profile.age}`);
  if (profile.income) parts.push(`₹${Number(profile.income).toLocaleString("en-IN")}`);
  if (profile.state) parts.push(profile.state);
  if (profile.category) parts.push(translatedCategory((categoryLabels && categoryLabels[profile.category]) || profile.category, t));
  return parts.length ? parts.join(" · ") : t("anyProfile");
}

function translatedCategory(label, t) {
  const value = String(label || "").trim().toLowerCase().replace(/[_-]+/g, " ");
  if (value.includes("farmer")) return t("catFarmers");
  if (value.includes("student")) return t("catStudents");
  if (value.includes("woman") || value.includes("women")) return t("catWomen");
  if (value.includes("senior")) return pt(t, "categorySenior");
  if (value.includes("disability") || value.includes("disabled")) return pt(t, "categoryDisability");
  if (value.includes("unemployed")) return pt(t, "categoryUnemployed");
  if (value.includes("bpl") || value.includes("low income")) return pt(t, "categoryLowIncome");
  return label;
}

function detectMessageLanguage(text) {
  const value = String(text || "");
  if (/[\u0B80-\u0BFF]/.test(value)) return "ta";
  if (/[\u0C00-\u0C7F]/.test(value)) return "te";
  if (/[\u0C80-\u0CFF]/.test(value)) return "kn";
  if (/[\u0D00-\u0D7F]/.test(value)) return "ml";
  if (/[\u0A80-\u0AFF]/.test(value)) return "gu";
  if (/[\u0A00-\u0A7F]/.test(value)) return "pa";
  if (/[\u0980-\u09FF]/.test(value)) return "bn";
  // Hindi and Marathi share Devanagari; use the stored message language when
  // available, otherwise Hindi is the safest default for legacy messages.
  if (/[\u0900-\u097F]/.test(value)) return "hi";
  return "en";
}

/* Build a question's text in the CURRENT interface language. Eligibility and
   life-event checks store `meta` instead of baking English into the text, so
   the chat bubble and the Recent list re-translate when the language changes. */
function questionLabel(msg, t, categoryLabels, eventLabels, lang) {
  if (!msg || !msg.meta) return msg ? (msg.translations?.[lang] || msg.text) : "";
  const prefix = msg.meta.eventOnly ? pt(t, "eventCheckPrefix") : t("eligCheckPrefix");
  return `${prefix}: ${formatProfileSummary(msg.meta.profile, categoryLabels, t, eventLabels)}`;
}

function EligibilityModal({ open, onClose, onSubmit, options, loading, error, t }) {
  const [age, setAge] = useState("");
  const [income, setIncome] = useState("");
  const [state, setState] = useState("");
  const [category, setCategory] = useState("");
  const [event, setEvent] = useState("");

  if (!open) return null;

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      age: age ? Number(age) : null,
      income: income ? Number(income) : null,
      state: state || null,
      category: category || null,
      event: event || null,
    });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="modal__title">
            <Filter size={16} />
            {t("eligTitle")}
          </div>
          <button className="modal__close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <p className="modal__subtitle">{t("eligIntro")}</p>
        <form className="eligibility-form" onSubmit={handleSubmit}>
          <label className="form-field">
            <span className="form-field__label">{t("age")}</span>
            <input
              type="number"
              min="0"
              max="120"
              className="form-field__input"
              placeholder="e.g. 45"
              value={age}
              onChange={(e) => setAge(e.target.value)}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">{t("income")}</span>
            <input
              type="number"
              min="0"
              className="form-field__input"
              placeholder="e.g. 150000"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">{t("state")}</span>
            <select className="form-field__input" value={state} onChange={(e) => setState(e.target.value)}>
              <option value="">{t("notSure")}</option>
              {options.states.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-field__label">{t("category")}</span>
            <select className="form-field__input" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">{t("general")}</option>
              {Object.entries(options.categories).map(([key, label]) => (
                <option key={key} value={key}>
                  {translatedCategory(label, t)}
                </option>
              ))}
            </select>
          </label>
          {Object.keys(options.events || {}).length > 0 && (
            <label className="form-field">
              <span className="form-field__label">{pt(t, "eventFieldLabel")}</span>
              <select className="form-field__input" value={event} onChange={(e) => setEvent(e.target.value)}>
                <option value="">{pt(t, "eventNone")}</option>
                {Object.entries(options.events).map(([key, label]) => (
                  <option key={key} value={key}>
                    {tEvent(t, label)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {error && <p className="admin-gate__error" role="alert">{error}</p>}
          <button className="eligibility-form__submit" type="submit" disabled={loading}>
            {loading ? t("searching") : t("find")}
          </button>
        </form>
      </div>
    </div>
  );
}

const REASON_GLYPH = { matched: "✓", unverified: "?", na: "–" };

/* Render one reason in the interface language. The server sends a stable `code`
   plus `params`; if this build doesn't know a code (newer backend), fall back to
   the server's English `note` rather than showing a raw key. */
function reasonText(reason, t, categoryLabels) {
  const key = "rs_" + reason.code;
  if (t(key) === key) return reason.note || "";
  const params = { ...(reason.params || {}) };
  for (const name of ["income", "ceiling"]) {
    if (params[name] !== undefined) params[name] = Number(params[name]).toLocaleString("en-IN");
  }
  if (params.category !== undefined) {
    params.category = translatedCategory((categoryLabels && categoryLabels[params.category]) || params.category, t);
  }
  return t(key, params);
}

function EligibilityCard({ match, onAskMore, t, lang, categoryLabels, verdict, comparing, onToggleCompare, translatedFields, translationBusy, translationError, onRetryTranslation }) {
  const isCentral = match.level === "Central";
  const [showOriginal, setShowOriginal] = useState(false);
  const [showWhy, setShowWhy] = useState(false);
  const reasons = match.reasons || [];
  const matchedReasons = reasons.filter((r) => r.status === "matched");
  const explanationReasons = matchedReasons.length ? matchedReasons : reasons.filter((r) => r.status === "unverified");
  const toVerifyCount = reasons.filter((r) => r.status === "unverified").length;

  const translated = translatedFields?.[`${match.slug}:eligibility_snippet`];
  const snippet = !showOriginal && translated ? translated : match.eligibility_snippet;

  useEffect(() => setShowOriginal(false), [lang]);

  return (
    <div className="eligibility-card">
      <div className="eligibility-card__top">
        <span className="eligibility-card__name">{match.scheme_name}</span>
        <span className={"eligibility-card__badge" + (isCentral ? " eligibility-card__badge--central" : "")}>
          {isCentral ? <Landmark size={11} /> : <MapPin size={11} />}
          {pt(t, match.level === "Central" ? "centralLevel" : "stateLevel")}
          {!isCentral && match.state ? ` · ${match.state}` : ""}
        </span>
      </div>
      {match.category && <div className="eligibility-card__category">{translatedCategory(match.category, t)}</div>}
      {snippet && <p className="eligibility-card__snippet">{snippet}</p>}
      {explanationReasons.length > 0 && (
        <p className="eligibility-card__why"><strong>{pt(t, "whyMatchedLabel")}</strong> {explanationReasons.map((r) => reasonText(r, t, categoryLabels)).join(" · ")}</p>
      )}
      <div className="eligibility-card__documents">
        <strong>{pt(t, "schemeDocuments")}</strong>
        {match.documents_needed?.length ? (
          <ul>{match.documents_needed.map((doc) => <li key={doc.key}>{t(`doc:${doc.key}`) === `doc:${doc.key}` ? doc.label : t(`doc:${doc.key}`)}</li>)}</ul>
        ) : <p>{translatedFields?.[`${match.slug}:documents_note`] || match.documents_note || pt(t, "schemeDocumentsUnknown")}</p>}
      </div>
      {translationError && <p className="eligibility-card__error" role="alert">{translationError}</p>}
      <VerdictBlock verdict={verdict} t={t} />
      {reasons.length > 0 && (
        <div className="why">
          <button
            type="button"
            className="why__toggle"
            onClick={() => setShowWhy((v) => !v)}
            aria-expanded={showWhy}
          >
            {showWhy ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {showWhy ? t("hideReasons") : t("whyMatched")}
            {!showWhy && toVerifyCount > 0 && (
              <span className="why__badge">{t("toVerify", { n: toVerifyCount })}</span>
            )}
          </button>
          {showWhy && (
            <>
              <ul className="why__list">
                {reasons.map((r) => (
                  <li key={r.field} className={"why__item why__item--" + r.status}>
                    <span
                      className="why__glyph"
                      title={t(r.status === "matched" ? "statusMatched" : r.status === "unverified" ? "statusUnverified" : "statusNa")}
                      aria-label={t(r.status === "matched" ? "statusMatched" : r.status === "unverified" ? "statusUnverified" : "statusNa")}
                    >
                      {REASON_GLYPH[r.status] || "·"}
                    </span>
                    <span>{reasonText(r, t, categoryLabels)}</span>
                  </li>
                ))}
              </ul>
              <p className="why__note">{t("reasonsNote")}</p>
            </>
          )}
        </div>
      )}
      <div className="eligibility-card__actions">
        <button className="eligibility-card__ask" onClick={() => onAskMore(match.scheme_name)}>
          {t("askAbout")} <ArrowUpRight size={13} />
        </button>
        {onToggleCompare && (
          <button type="button" className={"eligibility-card__compare" + (comparing ? " eligibility-card__compare--on" : "")} onClick={() => onToggleCompare(match.slug)} aria-pressed={comparing}>
            <ArrowLeftRight size={13} /> {comparing ? pt(t, "compareSelected") : pt(t, "compareAction")}
          </button>
        )}
        {match.apply_url && (
          <a className="eligibility-card__apply" href={match.apply_url} target="_blank" rel="noopener noreferrer">
            {pt(t, "officialApply")} <ExternalLink size={12} />
          </a>
        )}
        {lang !== "en" && match.eligibility_snippet && (
          <button className="eligibility-card__translate" onClick={() => translated ? setShowOriginal((value) => !value) : onRetryTranslation()} disabled={translationBusy}>
            <LanguagesIcon size={12} />
            {translationBusy ? t("translating") : showOriginal ? t("translateCard") : translated ? t("showOriginal") : t("tryAgain")}
          </button>
        )}
      </div>
    </div>
  );
}


/* One eligibility / life-event result set: summary, the 6.7 AI-check button,
   the 6.5 document planner, and the cards. Verdicts are kept here, per result
   set, so checking one search never touches another. */
function EligibilityResults({ msg, t, lang, categoryLabels, describeFailure, onAskMore, onExport }) {
  const [verdicts, setVerdicts] = useState({});
  const [compareSlugs, setCompareSlugs] = useState([]);
  const [translatedFields, setTranslatedFields] = useState({});
  const [translationBusy, setTranslationBusy] = useState(false);
  const [translationError, setTranslationError] = useState(null);
  const translateFields = async (isCancelled = () => false) => {
    const fields = msg.matches.flatMap((scheme) => ["eligibility_snippet", "benefits_snippet", "documents_note"]
      .filter((field) => scheme[field])
      .map((field) => ({ key: `${scheme.slug}:${field}`, text: scheme[field] })));
    if (!fields.length || lang === "en") return;
    setTranslationBusy(true);
    setTranslationError(null);
    try {
      const response = await fetch(TRANSLATE_BATCH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texts: fields.map((field) => field.text), language: lang, source_language: "en" }),
      });
      if (!response.ok) throw new Error(await describeFailure(response, t("translateFailed"), t));
      const data = await response.json();
      if (!isCancelled()) setTranslatedFields(Object.fromEntries(fields.map((field, index) => [field.key, data.translations[index]])));
    } catch (error) {
      if (!isCancelled()) setTranslationError(error?.message || t("translateFailed"));
    } finally {
      if (!isCancelled()) setTranslationBusy(false);
    }
  };
  useEffect(() => {
    let cancelled = false;
    setTranslatedFields({});
    setTranslationError(null);
    setTranslationBusy(false);
    if (lang !== "en") translateFields(() => cancelled);
    return () => { cancelled = true; };
    // A selected-language change translates the result set in one model request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, msg]);
  const toggleCompare = (slug) => setCompareSlugs((prev) => prev.includes(slug)
    ? prev.filter((item) => item !== slug)
    : prev.length < 2 ? [...prev, slug] : [prev[1], slug]);
  const compared = msg.matches.filter((m) => compareSlugs.includes(m.slug));
  const request = msg.request || {};
  return (
    <>
      <p className="eligibility-summary">
        {t("matched", { n: msg.totalMatched })}
        {msg.totalMatched > msg.matches.length ? ` (${msg.matches.length}/${msg.totalMatched})` : ""}
        {" "}— {t("disclaimer")}
      </p>
      <VerifyBar
        profile={request}
        slugs={msg.matches.map((m) => m.slug).filter(Boolean)}
        onVerdicts={setVerdicts}
        describeFailure={describeFailure}
        t={t}
      />
      <DocumentPlanner request={request} t={t} />
      <button className="checklist-export" type="button" onClick={() => onExport(msg.matches)} disabled={!msg.matches.length}>
        <FileDown size={15} /> {pt(t, "exportChecklist")}
      </button>
      {compared.length === 2 && <SchemeComparison schemes={compared} t={t} translatedFields={translatedFields} translationBusy={translationBusy} translationError={translationError} />}
      <div className="eligibility-grid">
        {msg.matches.map((m) => (
          <EligibilityCard
            key={m.slug || m.scheme_name}
            match={m}
            t={t}
            lang={lang}
            categoryLabels={categoryLabels}
            verdict={verdicts[m.slug]}
            onAskMore={onAskMore}
            comparing={compareSlugs.includes(m.slug)}
            onToggleCompare={toggleCompare}
            translatedFields={translatedFields}
            translationBusy={translationBusy}
            translationError={translationError}
            onRetryTranslation={translateFields}
          />
        ))}
      </div>
    </>
  );
}

function SchemeComparison({ schemes, t, translatedFields, translationBusy, translationError }) {
  return (
    <section className="scheme-comparison" aria-label={pt(t, "comparisonTitle")}>
      <h3>{pt(t, "comparisonTitle")}</h3>
      <div className="scheme-comparison__grid">
        {schemes.map((scheme) => (
          <article className="scheme-comparison__item" key={scheme.slug}>
            <h4>{scheme.scheme_name}</h4>
            <p><strong>{pt(t, "comparisonEligibility")}</strong><br />{translatedFields?.[`${scheme.slug}:eligibility_snippet`] || scheme.eligibility_snippet || "—"}</p>
            <p><strong>{pt(t, "comparisonBenefits")}</strong><br />{translatedFields?.[`${scheme.slug}:benefits_snippet`] || scheme.benefits_snippet || "—"}</p>
            <p><strong>{pt(t, "schemeDocuments")}</strong><br />{scheme.documents_needed?.length ? scheme.documents_needed.map((d) => t(`doc:${d.key}`) === `doc:${d.key}` ? d.label : t(`doc:${d.key}`)).join(", ") : (translatedFields?.[`${scheme.slug}:documents_note`] || scheme.documents_note || pt(t, "schemeDocumentsUnknown"))}</p>
            {translationBusy && <small>{t("translating")}</small>}
            {translationError && <small className="eligibility-card__error" role="alert">{translationError}</small>}
            {scheme.apply_url && <a href={scheme.apply_url} target="_blank" rel="noopener noreferrer">{pt(t, "officialApply")} <ExternalLink size={12} /></a>}
          </article>
        ))}
      </div>
    </section>
  );
}

function LandingState({ onPick, onEvent, events, eventsBusy, t }) {
  return (
    <div className="landing">
      <NetworkBackdrop />
      <div className="landing__content">
        <div className="landing__eyebrow">
          <BookOpenCheck size={14} /> {pt(t, "landingLibrary")}
        </div>
        <div className="landing__intro">
          <div>
            <p className="landing__kicker">{pt(t, "landingDesk")}</p>
            <h1 className="landing__heading">{t("heading")}</h1>
            <p className="landing__subheading">{t("subheading")}</p>
          </div>
          <div className="landing__dossier" aria-hidden="true">
            <div className="landing__dossier-top"><LibraryBig size={17} /> {pt(t, "landingDossier")}</div>
            <div className="landing__dossier-line landing__dossier-line--wide" />
            <div className="landing__dossier-line" />
            <div className="landing__dossier-line landing__dossier-line--short" />
            <div className="landing__dossier-footer"><span /> {pt(t, "landingFlow")}</div>
          </div>
        </div>
        <div className="landing__prompt-label">{t("beginWith")}</div>
        <div className="landing__grid">
          {SUGGESTIONS.map((english, index) => {
            const key = "sug" + (index + 1);
            const tr = t(key);
            const q = tr && tr !== key ? tr : english; // English fallback
            return (
            <button key={key} className="suggestion-card" onClick={() => onPick(q)}>
              <span className="suggestion-card__index">0{index + 1}</span>
              <span className="suggestion-card__question">{q}</span>
              <ArrowUpRight size={16} aria-hidden="true" />
            </button>
            );
          })}
        </div>
        <EventChips events={events} onPick={onEvent} disabled={eventsBusy} t={t} />
      </div>
    </div>
  );
}

function Sidebar({
  open,
  onClose,
  threads,
  activeThreadId,
  onNewChat,
  onSelectThread,
  onDeleteThread,
  onCategory,
  onOpenEligibility,
  status,
  t,
  lang,
  categoryLabels,
  eventLabels,
}) {
  return (
    <>
      {open && <div className="sidebar__backdrop" onClick={onClose} />}
      <aside className={"sidebar" + (open ? " sidebar--open" : "")}>
        <div className="sidebar__top">
          <div className="sidebar__atlas">
            <Logo size={22} />
            <span>{pt(t, "landingDossier")}<br />SchemeSetu</span>
          </div>
          <button className="sidebar__close" onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>
        <button className="sidebar__new-chat" onClick={onNewChat}>
          <Plus size={16} />
          {t("newChat")}
        </button>
        <button className="sidebar__eligibility-btn" onClick={onOpenEligibility}>
          <ClipboardCheck size={16} />
          {t("checkElig")}
        </button>

        <div className="sidebar__section">
          <span className="sidebar__label">{t("explore")}</span>
          <div className="sidebar__categories">
            {CATEGORIES.map(({ labelKey, icon: Icon, query }) => (
              <button key={labelKey} className="sidebar__category" onClick={() => onCategory(query)}>
                <Icon size={15} />
                {t(labelKey)}
              </button>
            ))}
          </div>
        </div>

        {threads.length > 0 && (
          <div className="sidebar__section sidebar__section--grow">
            <span className="sidebar__label">{t("recent")}</span>
            <div className="sidebar__threads">
              {threads.map((th) => (
                <div className="sidebar__thread-row" key={th.id}>
                  <button
                    className={"sidebar__thread" + (th.id === activeThreadId ? " sidebar__thread--active" : "")}
                    onClick={() => onSelectThread(th.id)}
                  >
                    {th.first
                      ? questionLabel(th.first, t, categoryLabels, eventLabels, lang).slice(0, 48)
                      : pt(t, "conversation")}
                  </button>
                  <button
                    type="button"
                    className="sidebar__icon-btn"
                    onClick={() => onDeleteThread(th.id)}
                    aria-label="Delete this chat"
                    title="Delete this chat"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="sidebar__status">
          <StatusDot status={status} />
          {status === "connected" && t("connected")}
          {status === "checking" && t("checking")}
          {status === "offline" && t("offline")}
        </div>
      </aside>
    </>
  );
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [status, setStatus] = useState("checking");
  const [threads, setThreads] = useState(loadThreads);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const activeIdRef = useRef(null);
  const [eligibilityModalOpen, setEligibilityModalOpen] = useState(false);
  const [eligibilityLoading, setEligibilityLoading] = useState(false);
  const [eligibilityError, setEligibilityError] = useState(null);
  const [eligibilityOptions, setEligibilityOptions] = useState({ states: [], categories: {}, events: {} });
  const [lang, setLang] = useState(loadSavedLanguage);
  const [listening, setListening] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [voiceNote, setVoiceNote] = useState(null);
  const recognizerRef = useRef(null);

  const t = makeT(lang);
  const langInfo = languageInfo(lang);

  const threadEndRef = useRef(null);
  const inputRef = useRef(null);
  const lastQuestionRef = useRef("");
  const abortRef = useRef(null);
  const [theme, setTheme] = useState(getInitialTheme);
  const translatingRef = useRef(new Set());
  const [busyTranslate, setBusyTranslate] = useState({});
  const [translationErrors, setTranslationErrors] = useState({});
  const [translationRetryVersion, setTranslationRetryVersion] = useState(0);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    document.documentElement.lang = lang;
    saveLanguage(lang);
  }, [lang]);

  // Stop the mic and any read-aloud if the page is left.
  useEffect(
    () => () => {
      stopSpeaking();
      recognizerRef.current?.abort?.();
    },
    []
  );

  useEffect(() => {
    if (!voiceNote) return undefined;
    const id = setTimeout(() => setVoiceNote(null), 6000);
    return () => clearTimeout(id);
  }, [voiceNote]);

  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, [input]);

  useEffect(() => {
    fetch(`${API_BASE}/`)
      .then((r) => (r.ok ? setStatus("connected") : setStatus("offline")))
      .catch(() => setStatus("offline"));
  }, []);

  useEffect(() => {
    fetch(ELIGIBILITY_OPTIONS_URL)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => setEligibilityOptions({ states: data.states || [], categories: data.categories || {}, events: data.events || {} }))
      .catch(() => {}); // form still works with empty dropdowns if this fails
  }, []);

  // Translate an answer into `target` (cached on the message as translations[target]).
  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next, true);
  }

  async function getMessageTranslation(index, msg, target) {
    const cached = msg.translations && msg.translations[target];
    if (cached) return cached;
    const sourceLanguage = msg.lang || detectMessageLanguage(msg.text);
    if (sourceLanguage === target) return msg.text;
    const res = await fetch(TRANSLATE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: msg.text.slice(0, 3000),
          language: target,
        source_language: sourceLanguage,
        }),
    });
    if (!res.ok) throw new Error(await describeFailure(res, t("translateFailed"), t));
    const translated = (await res.json()).translation;
    setMessages((prev) =>
      prev.map((m, k) => (k === index ? { ...m, translations: { ...(m.translations || {}), [target]: translated } } : m))
    );
    return translated;
  }

  async function translateMessageAt(index, msg) {
    const key = index + ":" + lang;
    if (translatingRef.current.has(key)) return;
    translatingRef.current.add(key);
    setBusyTranslate((p) => ({ ...p, [key]: true }));
    try {
      await getMessageTranslation(index, msg, lang);
      setTranslationErrors((previous) => {
        const next = { ...previous };
        delete next[key];
        return next;
      });
      return true;
    } catch (error) {
      const message = error?.message || t("translateFailed");
      setTranslationErrors((previous) => ({ ...previous, [key]: message }));
      setVoiceNote(message);
      return false;
    } finally {
      translatingRef.current.delete(key);
      setBusyTranslate((p) => ({ ...p, [key]: false }));
    }
  }

  async function retryTranslationAt(index, msg) {
    const translated = await translateMessageAt(index, msg);
    if (translated) setTranslationRetryVersion((version) => version + 1);
  }

  // The text to show for an answer in the CURRENT language.
  function answerText(msg) {
    const sourceLanguage = msg.lang || detectMessageLanguage(msg.text);
    if (sourceLanguage === lang) return msg.text;
    if (msg.isFallback) return t("noMatch");
    return (msg.translations && msg.translations[lang]) || msg.text;
  }

  // Translate every existing user question and answer when the language changes.
  // This also handles older saved messages that do not have a language field.
  const translationQueueKey = messages
    .map((msg, i) => `${i}:${msg.role}:${msg.lang || ""}:${msg.text?.length || 0}`)
    .join("|");
  useEffect(() => {
    let cancelled = false;
    async function translateExistingMessages() {
      for (let i = 0; i < messages.length; i++) {
        const msg = messages[i];
        if (
          cancelled || !["question", "answer"].includes(msg.role) || msg.meta || msg.isFallback
        ) continue;
        const sourceLanguage = msg.lang || detectMessageLanguage(msg.text);
        if (sourceLanguage === lang || (msg.translations && msg.translations[lang])) continue;
        const translated = await translateMessageAt(i, msg);
        if (!translated) break;
      }
    }
    translateExistingMessages();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, translationQueueKey, activeThreadId, translationRetryVersion]);

  async function ask(question) {
    if (!question.trim() || loading) return;

    lastQuestionRef.current = question;
    const askLang = lang;
    stopSpeaking();
    setSpeakingIndex(null);

    // Snapshot history from the thread as it stands BEFORE this question,
    // so a retry doesn't accidentally include the question itself.
    const history = buildHistory(messages);

    // Resending an unanswered question must not add a second copy of it.
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      return last && last.role === "question" && last.text === question
        ? prev
        : [...prev, { role: "question", text: question, lang: detectMessageLanguage(question) }];
    });
    setInput("");
    setLoading(true);
    setError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history, language: askLang }),
        signal: controller.signal,
      });
      if (!response.ok) {
        setError(await describeFailure(response, t("errGeneric"), t));
        return;
      }
      const data = await response.json();
      setStatus("connected");
      setMessages((prev) => {
        const next = [...prev];
        // Remember the English form of the question we just asked: it is what
        // gets sent back as history, so follow-ups keep resolving scheme names.
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "question") {
            next[i] = { ...next[i], englishQuestion: data.english_question || next[i].text };
            break;
          }
        }
        next.push({
          role: "answer",
          text: data.answer,
          // A "could not find" answer must not point at source records: they were
          // only the closest matches, not evidence for anything.
          sources: data.is_fallback ? [] : data.sources || [],
          isFallback: Boolean(data.is_fallback),
          lang: askLang,
        });
        return next;
      });
    } catch (err) {
      if (err && err.name === "AbortError") {
        // The user pressed Stop: show a calm note with the Resend button.
        setError(pt(t, "stopped"));
      } else {
        setStatus("offline");
        setError(await describeFailure(null, "", t));
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  }

  function handleStop() {
    abortRef.current?.abort();
  }

  async function handleEligibilitySubmit(profile) {
    setEligibilityLoading(true);
    setEligibilityError(null);
    try {
      const response = await fetch(ELIGIBILITY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (!response.ok) {
        setEligibilityError(await describeFailure(response, t("errEligGeneric"), t));
        return;
      }
      const data = await response.json();
      const summary = formatProfileSummary(profile, eligibilityOptions.categories, t, eligibilityOptions.events);
      const eventOnly = Boolean(
        profile.event && !profile.age && !profile.income && !profile.state && !profile.category
      );
      const prefix = eventOnly ? pt(t, "eventCheckPrefix") : t("eligCheckPrefix");
      setMessages((prev) => [
        ...prev,
        { role: "question", text: `${prefix}: ${summary}`, meta: { profile, eventOnly } },
        {
          role: "eligibility",
          totalMatched: data.total_matched,
          matches: data.matches || [],
          request: profile,
          event: profile.event || null,
        },
      ]);
      setEligibilityModalOpen(false);
    } catch (err) {
      setEligibilityError(await describeFailure(null, "", t));
    } finally {
      setEligibilityLoading(false);
    }
  }

  /* 6.6: a life-event chip is just an eligibility search with only `event` set. */
  async function handleEventPick(key) {
    if (eligibilityLoading) return;
    await handleEligibilitySubmit({ age: null, income: null, state: null, category: null, event: key });
  }

  function handleOpenEligibility() {
    setEligibilityError(null);
    setSidebarOpen(false);
    setEligibilityModalOpen(true);
  }

  function handleSubmit(e) {
    e.preventDefault();
    ask(input);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask(input);
    }
  }

  function handleDeleteThread(id) {
    setThreads((prev) => prev.filter((th) => th.id !== id));
    if (id === activeThreadId) {
      setMessages([]);
      setActiveThreadId(null);
      activeIdRef.current = null;
    }
  }

  // Save the thread list in this browser whenever it changes.
  useEffect(() => {
    persistThreads(threads);
  }, [threads]);

  // Auto-save the open chat shortly after each finished answer.
  useEffect(() => {
    if (loading || messages.length === 0) return;
    const open = threads.find((th) => th.id === activeIdRef.current);
    if (open && open.messages === messages) return; // just opened from the list: nothing new
    const timer = setTimeout(() => {
      const first = messages.find((m) => m.role === "question");
      let id = activeIdRef.current;
      if (!id) {
        id = newThreadId();
        activeIdRef.current = id;
        setActiveThreadId(id);
      }
      setThreads((prev) =>
        prev.some((th) => th.id === id)
          ? prev.map((th) => (th.id === id ? { ...th, first, messages } : th))
          : [{ id, first, messages }, ...prev]
      );
    }, 1200);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, loading]);

  function handleNewChat() {
    stopSpeaking();
    setSpeakingIndex(null);
    if (messages.length > 0) {
      const first = messages.find((m) => m.role === "question");
      // Re-opening a saved thread and clicking New chat must UPDATE it, not add a duplicate.
      const id = activeThreadId || newThreadId();
      setThreads((prev) =>
        prev.some((th) => th.id === id)
          ? prev.map((th) => (th.id === id ? { ...th, first, messages } : th))
          : [{ id, first, messages }, ...prev]
      );
    }
    setMessages([]);
    setError(null);
    setActiveThreadId(null);
    activeIdRef.current = null;
    setSidebarOpen(false);
  }

  function handleSelectThread(id) {
    const thread = threads.find((th) => th.id === id);
    if (thread) {
      stopSpeaking();
      setSpeakingIndex(null);
      setMessages(thread.messages);
      setActiveThreadId(id);
      activeIdRef.current = id;
      setError(null);
      setSidebarOpen(false);
    }
  }

  function handleCategory(query) {
    setSidebarOpen(false);
    ask(query);
  }

  function insertTemplate(text) {
    setInput(text);
    inputRef.current?.focus();
  }

  function handleLanguageChange(code) {
    recognizerRef.current?.abort?.();
    stopSpeaking();
    setSpeakingIndex(null);
    setVoiceNote(null);
    setLang(code);
  }

  function toggleMic() {
    if (!voiceInputSupported()) {
      setVoiceNote(t("voiceUnsupported"));
      return;
    }
    if (listening) {
      recognizerRef.current?.stop();
      return;
    }
    stopSpeaking();
    setSpeakingIndex(null);

    const base = input.trim() ? input.trim() + " " : ""; // keep anything already typed
    const recognizer = createRecognizer({
      lang: langInfo.listen || langInfo.speech,
      onText: (text) => setInput(base + text),
      onError: (code) => {
        if (code === "aborted") return;
        if (code === "not-allowed" || code === "service-not-allowed") setVoiceNote(t("micDenied"));
        else if (code === "no-speech") setVoiceNote(t("noSpeech"));
        else setVoiceNote(t("voiceError"));
      },
      onEnd: (text) => {
        setListening(false);
        recognizerRef.current = null;
        if (text) inputRef.current?.focus();
        if (text && transcriptScriptMismatch(text, lang)) {
          setVoiceNote(t("scriptHint", { lang: langInfo.native }));
        }
      },
    });
    recognizerRef.current = recognizer;
    try {
      recognizer.start();
      setListening(true);
      setVoiceNote(null);
    } catch {
      recognizerRef.current = null;
      setVoiceNote(t("voiceError"));
    }
  }

  async function toggleSpeak(index, msg) {
    if (speakingIndex === index) {
      stopSpeaking();
      setSpeakingIndex(null);
      return;
    }
    if (!voiceOutputSupported()) {
      setVoiceNote(t("voiceError"));
      return;
    }

    let text = msg.text;
    let speakLang = msg.lang || "en";

    // The answer was written in another language than the one selected now:
    // use (or fetch) its translation so Listen follows the UI language.
    if (speakLang !== lang && !msg.isFallback) {
      const cached = msg.translations && msg.translations[lang];
      if (cached) {
        text = cached;
      } else {
        setSpeakingIndex(index); // shows "Stop" while translating
        try {
          text = await getMessageTranslation(index, msg, lang);
        } catch {
          setVoiceNote(t("voiceError"));
          setSpeakingIndex(null);
          return;
        }
      }
      speakLang = lang;
    } else if (speakLang !== lang) {
      text = t("noMatch");
      speakLang = lang;
    }

    const info = languageInfo(speakLang);
    if (!hasVoiceFor(info.speech)) setVoiceNote(t("ttsMissing", { lang: info.native }));
    setSpeakingIndex(index);
    speak(text, info.speech, {
      onEnd: () => setSpeakingIndex((current) => (current === index ? null : current)),
    });
  }

  // Life-event chips get their labels translated here (Planner.jsx stays untouched).
  const translatedEvents = Object.fromEntries(
    Object.entries(eligibilityOptions.events || {}).map(([k, label]) => [k, tEvent(t, label)])
  );

  const uniqueSourceCount = new Set(
    messages.filter((m) => m.role === "answer").flatMap((m) => m.sources)
  ).size;

  return (
    <div className="app">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        threads={threads}
        activeThreadId={activeThreadId}
        onNewChat={handleNewChat}
        onSelectThread={handleSelectThread}
        onDeleteThread={handleDeleteThread}
        onCategory={handleCategory}
        onOpenEligibility={handleOpenEligibility}
        status={status}
        t={t}
        lang={lang}
        categoryLabels={eligibilityOptions.categories}
        eventLabels={eligibilityOptions.events}
      />

      <EligibilityModal
        open={eligibilityModalOpen}
        onClose={() => setEligibilityModalOpen(false)}
        onSubmit={handleEligibilitySubmit}
        options={eligibilityOptions}
        loading={eligibilityLoading}
        error={eligibilityError}
        t={t}
      />

      <div className="main">
        <header className="topbar">
          <button className="topbar__menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
            <Menu size={19} />
          </button>
          <div className="topbar__brand">
            <Logo />
            <span className="topbar__wordmark">SchemeSetu</span>
          </div>
          {messages.length > 0 ? (
            <div className="topbar__meta">
              SchemeSetu
              {uniqueSourceCount > 0 && <> · {uniqueSourceCount} {t("sourceDocs").toLowerCase()}</>}
            </div>
          ) : (
            <div className="topbar__status">
              <StatusDot status={status} />
              {status === "connected" ? t("connected") : status === "checking" ? t("checking") : t("offline")}
            </div>
          )}
          <label className="lang-select">
            <LanguagesIcon size={15} aria-hidden="true" />
            <select value={lang} onChange={(e) => handleLanguageChange(e.target.value)} aria-label={t("language")}>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? pt(t, "themeLight") : pt(t, "themeDark")}
            title={theme === "dark" ? pt(t, "themeLight") : pt(t, "themeDark")}
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </header>

        {messages.length === 0 ? (
          <>
            <LandingState
              onPick={(q) => ask(q)}
              onEvent={handleEventPick}
              events={translatedEvents}
              eventsBusy={eligibilityLoading}
              t={t}
            />
            {error && (
              <div className="error-card" role="alert">
                {error}
                <button className="error-card__retry" onClick={() => ask(lastQuestionRef.current)}>
                  <RotateCcw size={13} />
                  {t("tryAgain")}
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="thread">
            {messages.map((msg, i) =>
              msg.role === "question" ? (
                <div className="msg-question" key={i}>
                  {(() => {
                    const sourceLanguage = msg.lang || detectMessageLanguage(msg.text);
                    const translating = !msg.meta && sourceLanguage !== lang && !msg.translations?.[lang] && busyTranslate[i + ":" + lang];
                    return translating ? t("translating") : questionLabel(msg, t, eligibilityOptions.categories, eligibilityOptions.events, lang);
                  })()}
                  {translationErrors[i + ":" + lang] && (
                    <button type="button" className="listen-btn" onClick={() => retryTranslationAt(i, msg)}>
                      {t("tryAgain")}
                    </button>
                  )}
                </div>
              ) : msg.role === "eligibility" ? (
                <div className="msg-answer" key={i}>
                  <div className="msg-answer__caption msg-answer__caption--eligibility">
                    <span /> {msg.event ? pt(t, "eventCaption") : t("eligCaption")}
                  </div>
                  {msg.matches.length === 0 ? (
                    <div className="msg-answer__body msg-answer__body--fallback">{t("noMatch")}</div>
                  ) : (
                    <EligibilityResults
                      msg={msg}
                      t={t}
                      lang={lang}
                      categoryLabels={eligibilityOptions.categories}
                      describeFailure={describeFailure}
                      onAskMore={(name) => ask(`Tell me more about ${name}`)}
                      onExport={(items) => exportChecklist(items, pt(t, "eligibleChecklistTitle"), t)}
                    />
                  )}
                </div>
              ) : (
                <div className="msg-answer" key={i}>
                  <div className="msg-answer__caption"><span /> {t("caption")}</div>
                  <div
                    className={
                      "msg-answer__body" +
                      (msg.isFallback ? " msg-answer__body--fallback" : "")
                    }
                  >
                    <ReactMarkdown>
                      {(() => {
                        const sourceLanguage = msg.lang || detectMessageLanguage(msg.text);
                        const translating = sourceLanguage !== lang && !msg.isFallback && !msg.translations?.[lang] && busyTranslate[i + ":" + lang];
                        return translating ? t("translating") : answerText(msg);
                      })()}
                    </ReactMarkdown>
                  </div>
                  {(msg.lang || detectMessageLanguage(msg.text)) !== lang && !msg.isFallback && !(msg.translations && msg.translations[lang]) && (
                    <div className="msg-answer__actions">
                      <button
                        type="button"
                        className="listen-btn"
                        onClick={() => retryTranslationAt(i, msg)}
                        disabled={Boolean(busyTranslate[i + ":" + lang])}
                      >
                        {busyTranslate[i + ":" + lang] ? t("translating") : t("translateCard")}
                      </button>
                    </div>
                  )}
                  {translationErrors[i + ":" + lang] && (
                    <p className="voice-note" role="alert">{translationErrors[i + ":" + lang]}</p>
                  )}
                  {voiceOutputSupported() && (
                    <div className="msg-answer__actions">
                      <button
                        type="button"
                        className={"listen-btn" + (speakingIndex === i ? " listen-btn--on" : "")}
                        onClick={() => toggleSpeak(i, msg)}
                        aria-pressed={speakingIndex === i}
                      >
                        {speakingIndex === i ? <Square size={12} /> : <Volume2 size={14} />}
                        {speakingIndex === i ? t("stopSpeaking") : t("listen")}
                      </button>
                    </div>
                  )}
                  {msg.sources.length > 0 && (
                    <div className="source-block">
                      <span className="source-block__label">{t("sourceDocs")}</span>
                      <div className="source-block__cards">
                        <SourceCards sources={msg.sources} t={t} lang={lang} />
                      </div>
                    </div>
                  )}
                  {msg.sources.length > 0 && <DocumentPlanner names={msg.sources} t={t} />}
                </div>
              )
            )}

            {loading && <LoadingIndicator t={t} />}
            {error && (
              <div className="error-card">
                {error}
                <button className="error-card__retry" onClick={() => ask(lastQuestionRef.current)}>
                  <RotateCcw size={13} />
                  {t("tryAgain")}
                </button>
              </div>
            )}
            <div ref={threadEndRef} />
          </div>
        )}

        <div className="composer">
          <div className="composer__templates">
            {QUICK_TEMPLATES.map((tpl) => {
              const tr = (suffix, fallback) => {
                const k = "tpl" + tpl.id + suffix;
                const v = t(k);
                return v && v !== k ? v : fallback;
              };
              return (
                <button key={tpl.id} className="template-chip" onClick={() => insertTemplate(tr("Text", tpl.text))}>
                  {tr("", tpl.label)}
                </button>
              );
            })}
          </div>
          <form className="composer__form" onSubmit={handleSubmit}>
            <textarea
              ref={inputRef}
              className="composer__input"
              placeholder={listening ? `${langInfo.native} · ${t("listening")}` : t("placeholder")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              type="button"
              className={"composer__mic" + (listening ? " composer__mic--on" : "")}
              onClick={toggleMic}
              aria-label={listening ? t("listening") : t("speak")}
              aria-pressed={listening}
              title={listening ? t("listening") : t("speak")}
            >
              {listening ? <Square size={14} /> : <Mic size={17} />}
            </button>
            {loading ? (
              <button className="composer__send" type="button" onClick={handleStop} aria-label={pt(t, "stopLabel")} title={pt(t, "stopLabel")}>
                <Square size={14} />
              </button>
            ) : (
              <button className="composer__send" type="submit" disabled={!input.trim()} aria-label={pt(t, "sendButton")}>
                <Send size={16} />
              </button>
            )}
          </form>
          {voiceNote && (
            <p className="voice-note" role="status">
              {voiceNote}
            </p>
          )}
          <p className="composer__hint">{t("hint")}</p>
        </div>
      </div>
    </div>
  );
}

/* Routes to the admin dashboard on /admin, otherwise the normal chat app.
   This check lives in a separate component (not inside App itself) so it
   never runs between App's hook calls -- App and AdminPage are siblings,
   each with their own independent hook sequence, so there's no risk of
   violating the rules of hooks even if the path were ever to change. */
function Root() {
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/admin")) {
    return <AdminPage />;
  }
  return <App />;
}

export default Root;
