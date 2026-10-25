import { useEffect, useState } from "react";
import { CalendarHeart, FolderCheck, ShieldCheck, ChevronDown, ChevronUp, Baby, Briefcase, Store, Gem, Armchair, GraduationCap, HeartPulse, CloudRain } from "lucide-react";
import { pt } from "./planner_strings";
import { API_BASE } from "./config";

const API = API_BASE;
export const DOCUMENT_PLAN_URL = `${API}/documents/plan`;
export const DOCS_FOR_SCHEMES_URL = `${API}/documents/for-schemes`;
export const VERIFY_URL = `${API}/eligibility/verify`;
export const VERIFY_MAX = 5; // keep in sync with MAX_SCHEMES in verify.py

const EVENT_ICONS = {
  new_baby: Baby,
  lost_job: Briefcase,
  start_business: Store,
  daughter_marriage: Gem,
  retiring: Armchair,
  child_education: GraduationCap,
  health_emergency: HeartPulse,
  crop_loss: CloudRain,
};

/* Translated document name: i18n_extra has "doc:<key>" entries; falls back to the server's English label. */
function docLabel(t, d) {
  const k = "doc:" + d.key;
  const v = t(k);
  return v && v !== k ? v : d.label;
}

/* ---------------------------------------------------------------- 6.6 */
/* Row of life-event chips for the landing screen. `events` is the
   {key: label} map from /eligibility/options. */
export function EventChips({ events, onPick, disabled, t }) {
  const entries = Object.entries(events || {});
  if (entries.length === 0) return null;
  return (
    <div className="events">
      <div className="landing__prompt-label">{pt(t, "eventsLabel")}</div>
      <p className="events__hint">{pt(t, "eventsHint")}</p>
      <div className="events__chips">
        {entries.map(([key, label]) => {
          const Icon = EVENT_ICONS[key] || CalendarHeart;
          return (
            <button key={key} type="button" className="event-chip" disabled={disabled} onClick={() => onPick(key, label)}>
              <Icon size={14} aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- 6.5 */
/* Collapsible "documents you'll need" checklist. `request` is the profile /
   event that produced the results ({age, income, state, category, event}).
   Nothing is fetched until the panel is opened, and every tick re-asks the
   server (no LLM, ~0.05s) so the counts always come from one source. */
export function DocumentPlanner({ request, names, t }) {
  // `names` (scheme names, e.g. a chat answer's sources) -> documents for those
  // schemes; otherwise `request` (profile / life event) -> documents for all matches.
  const bySchemes = Array.isArray(names);
  const [open, setOpen] = useState(false);
  const [have, setHave] = useState([]);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(bySchemes ? DOCS_FOR_SCHEMES_URL : DOCUMENT_PLAN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bySchemes ? { names, have } : { ...request, have }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => !cancelled && setPlan(data))
      .catch(() => !cancelled && setError(pt(t, "docsError")))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, have]);

  function toggleHave(key) {
    setHave((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  return (
    <div className="docplan">
      <button type="button" className="docplan__toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <FolderCheck size={14} />
        {open ? pt(t, "docsHide") : pt(t, "docsToggle")}
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {open && (
        <div className="docplan__body">
          {error && <p className="docplan__error" role="alert">{error}</p>}
          {!plan && loading && <p className="docplan__muted">{pt(t, "docsLoading")}</p>}
          {plan && (
            <>
              <p className="docplan__muted">
                {pt(t, bySchemes ? "docsIntroAnswer" : "docsIntro", { total: plan.total_schemes })}
              </p>
              <div className="docplan__stats">
                <span className="docplan__stat docplan__stat--ready">{pt(t, "docsReady", { n: plan.ready_now })}</span>
                {plan.docs_unknown > 0 && (
                  <span className="docplan__stat">{pt(t, "docsUnknown", { n: plan.docs_unknown })}</span>
                )}
              </div>
              {plan.documents.length === 0 ? (
                <p className="docplan__muted">{pt(t, "docsNone")}</p>
              ) : (
                <ul className="docplan__list" style={{ opacity: loading ? 0.6 : 1 }}>
                  {plan.documents.map((d) => (
                    <li key={d.key} className={"docplan__item" + (d.have ? " docplan__item--have" : "")}>
                      <label className="docplan__row">
                        <input type="checkbox" checked={d.have} onChange={() => toggleHave(d.key)} />
                        <span className="docplan__label">{docLabel(t, d)}</span>
                        <span className="docplan__count">{pt(t, "docsNeededBy", { n: d.needed_by })}</span>
                      </label>
                      {!d.have && d.unlocks > 0 && (
                        <p className="docplan__unlock" title={d.unlock_examples.join("\n")}>
                          {pt(t, "docsUnlocks", { n: d.unlocks })}
                          {d.unlock_examples.length > 0 && <span> · {d.unlock_examples.join(", ")}</span>}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <p className="docplan__note">{pt(t, "docsNote")}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- 6.7 */
/* Button + status line. Calls onVerdicts({slug: verdict}) when done.
   `profile` is {age, income, state, category}; `slugs` the schemes to check. */
export function VerifyBar({ profile, slugs, onVerdicts, describeFailure, t }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const hasProfile = Boolean(profile && (profile.age || profile.income || profile.state || profile.category));
  const toCheck = slugs.slice(0, VERIFY_MAX);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(VERIFY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slugs: toCheck,
          age: profile.age || null,
          income: profile.income || null,
          state: profile.state || null,
          category: profile.category || null,
        }),
      });
      if (!response.ok) {
        setError(await describeFailure(response, pt(t, "verifyFailed"), t));
        return;
      }
      const data = await response.json();
      const bySlug = {};
      for (const v of data.verdicts || []) bySlug[v.slug] = v;
      onVerdicts(bySlug);
      setDone(true);
    } catch {
      setError(await describeFailure(null, "", t));
    } finally {
      setBusy(false);
    }
  }

  if (!hasProfile) return <p className="verify__hint">{pt(t, "verifyNeedProfile")}</p>;
  return (
    <div className="verify">
      <button type="button" className="admin-btn admin-btn--saffron" onClick={run} disabled={busy || toCheck.length === 0}>
        <ShieldCheck size={14} />
        {busy ? pt(t, "verifyWorking") : pt(t, "verifyButton", { n: toCheck.length })}
      </button>
      {(done || busy) && <p className="verify__hint">{pt(t, "verifyIntro")}</p>}
      {error && <p className="docplan__error" role="alert">{error}</p>}
    </div>
  );
}

const VERDICT_KEYS = { likely: "verdictLikely", unclear: "verdictUnclear", not_eligible: "verdictNotEligible" };

/* Shown inside a scheme card once its verdict is in. */
export function VerdictBlock({ verdict, t }) {
  if (!verdict) return null;
  return (
    <div className={"verdict verdict--" + verdict.verdict}>
      <div className="verdict__head">
        <span className="verdict__badge">{pt(t, VERDICT_KEYS[verdict.verdict] || "verdictUnclear")}</span>
      </div>
      {verdict.reason && <p className="verdict__reason">{verdict.reason}</p>}
      {verdict.quote && (
        <blockquote className="verdict__quote">
          <span className="verdict__quote-label">{pt(t, "verdictBasedOn")}</span> “{verdict.quote}”
        </blockquote>
      )}
    </div>
  );
}
