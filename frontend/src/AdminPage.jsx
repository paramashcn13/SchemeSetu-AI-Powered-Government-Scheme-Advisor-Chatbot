import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "./config";
import {
  Search,
  Plus,
  Pencil,
  Trash2,
  Upload,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  X,
  Landmark,
  MapPin,
} from "lucide-react";

const BASE_URL = API_BASE;
const PAGE_SIZE = 25;

const EMPTY_FORM = {
  scheme_name: "",
  slug: "",
  level: "Central",
  schemeCategory: "",
  tags: "",
  details: "",
  eligibility: "",
  benefits: "",
  application: "",
  documents: "",
};

/* ---- create/edit form, shown as a modal ---- */

function SchemeForm({ mode, initial, hint, onCancel, onSaved }) {
  const [form, setForm] = useState(initial || EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.scheme_name.trim()) {
      setError("Scheme name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const isEdit = mode === "edit";
      const url = isEdit
        ? `${BASE_URL}/admin/schemes/${initial.slug}`
        : `${BASE_URL}/admin/schemes`;
      const res = await fetch(url, {
        method: isEdit ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server responded with ${res.status}`);
      }
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const textFields = [
    ["details", "Details"],
    ["eligibility", "Eligibility"],
    ["benefits", "Benefits"],
    ["application", "Application process"],
    ["documents", "Documents required"],
  ];

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal admin-form-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="modal__title">{mode === "edit" ? "Edit scheme" : "New scheme"}</div>
          <button className="modal__close" onClick={onCancel} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="eligibility-form" onSubmit={handleSubmit}>
          {hint && (
            <div className="gap-hint">
              <strong>People asked{hint.count > 1 ? ` (${hint.count}×)` : ""}:</strong> “{hint.question}”
              <span className="gap-hint__note"> This reminder is not saved with the scheme.</span>
            </div>
          )}
          <label className="form-field">
            <span className="form-field__label">Scheme name *</span>
            <input
              className="form-field__input"
              value={form.scheme_name}
              onChange={(e) => update("scheme_name", e.target.value)}
            />
          </label>

          {mode === "create" && (
            <label className="form-field">
              <span className="form-field__label">Slug (optional — auto-generated if left blank)</span>
              <input
                className="form-field__input"
                value={form.slug}
                onChange={(e) => update("slug", e.target.value)}
              />
            </label>
          )}
          {mode === "edit" && (
            <label className="form-field">
              <span className="form-field__label">Slug (fixed, not editable)</span>
              <input className="form-field__input" value={form.slug} disabled />
            </label>
          )}

          <div className="admin-form__row">
            <label className="form-field">
              <span className="form-field__label">Level</span>
              <select className="form-field__input" value={form.level} onChange={(e) => update("level", e.target.value)}>
                <option value="Central">Central</option>
                <option value="State">State</option>
              </select>
            </label>
            <label className="form-field">
              <span className="form-field__label">Category</span>
              <input
                className="form-field__input"
                value={form.schemeCategory}
                onChange={(e) => update("schemeCategory", e.target.value)}
              />
            </label>
          </div>

          <label className="form-field">
            <span className="form-field__label">Tags (comma-separated)</span>
            <input className="form-field__input" value={form.tags} onChange={(e) => update("tags", e.target.value)} />
          </label>

          {textFields.map(([field, label]) => (
            <label className="form-field" key={field}>
              <span className="form-field__label">{label}</span>
              <textarea
                className="form-field__input admin-form__textarea"
                value={form[field]}
                onChange={(e) => update(field, e.target.value)}
                rows={3}
              />
            </label>
          ))}

          {error && <p className="admin-gate__error">{error}</p>}

          <div className="admin-form__actions">
            <button type="button" className="admin-btn admin-btn--ghost" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="eligibility-form__submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ---- 6.4: questions the assistant could not answer ---- */

function formatWhen(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString();
}

function GapsPanel({ onCreate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BASE_URL}/admin/gaps?limit=200`);
      if (!res.ok) throw new Error();
      setData(await res.json());
    } catch {
      setError("Could not load unanswered questions. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="gaps">
      <div className="gaps__head">
        <p className="gaps__intro">
          Questions the assistant answered with “not found”, most-asked first. If the same question keeps appearing,
          the data is missing a scheme: create it, reindex, then ask the question again to check.
        </p>
        <button className="admin-btn admin-btn--ghost" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? "admin-spin" : ""} /> Refresh
        </button>
      </div>

      {error && <p className="admin-gate__error">{error}</p>}

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Question</th>
              <th>Asked</th>
              <th>Last asked</th>
              <th>Closest scheme</th>
              <th title="How close the best-matching scheme text was (0–100%). The assistant needs 45% to answer.">Best match</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading && !data ? (
              <tr>
                <td colSpan={6} className="admin-table__empty">Loading…</td>
              </tr>
            ) : !data || data.gaps.length === 0 ? (
              <tr>
                <td colSpan={6} className="admin-table__empty">
                  Nothing unanswered yet. Questions the assistant can't answer will appear here.
                </td>
              </tr>
            ) : (
              data.gaps.map((g) => (
                <tr key={g.question + g.first_seen}>
                  <td className="admin-table__name">
                    {g.question}
                    {g.original_question && g.original_question !== g.question && (
                      <div className="admin-table__muted">{g.original_question}</div>
                    )}
                  </td>
                  <td>
                    <span className="gap-count">{g.count}×</span>
                    {g.languages.some((l) => l !== "en") && (
                      <span className="admin-table__muted"> {g.languages.join(", ")}</span>
                    )}
                  </td>
                  <td className="admin-table__muted">{formatWhen(g.last_seen)}</td>
                  <td className="admin-table__muted">{g.named_scheme || "—"}</td>
                  <td className="admin-table__muted">
                    {g.best_confidence === null ? "—" : `${Math.round(g.best_confidence * 100)}%`}
                  </td>
                  <td className="admin-table__actions">
                    <button className="admin-btn admin-btn--ghost" onClick={() => onCreate(g)}>
                      <Plus size={14} /> Create scheme from this
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="admin-pagination">
          <span>
            {data.unique_questions} unanswered question{data.unique_questions !== 1 ? "s" : ""} · {data.total_entries} time
            {data.total_entries !== 1 ? "s" : ""} asked in total
            {data.unique_questions > data.gaps.length ? ` · showing the top ${data.gaps.length}` : ""}
          </span>
        </div>
      )}
    </div>
  );
}

/* ---- the dashboard itself ---- */

export default function AdminPage() {
  const [schemes, setSchemes] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [listLoading, setListLoading] = useState(false);
  const [formState, setFormState] = useState(null); // null | {mode:'create'} | {mode:'edit', scheme}
  const [status, setStatus] = useState(null); // transient success/error banner
  const [reindexing, setReindexing] = useState(false);
  const [view, setView] = useState("schemes"); // "schemes" | "gaps"

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const fetchSchemes = useCallback(async () => {
    setListLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
      if (search.trim()) params.set("search", search.trim());
      const res = await fetch(`${BASE_URL}/admin/schemes?${params}`);
      const data = await res.json();
      setSchemes(data.schemes);
      setTotal(data.total);
    } catch (err) {
      setStatus({ type: "error", text: "Could not load schemes." });
    } finally {
      setListLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    fetchSchemes();
  }, [fetchSchemes]);

  // reset to page 1 whenever the search term changes
  useEffect(() => {
    setPage(1);
  }, [search]);

  async function handleDelete(scheme) {
    if (!window.confirm(`Delete "${scheme.scheme_name}"? This can't be undone until you re-add it.`)) return;
    try {
      const res = await fetch(`${BASE_URL}/admin/schemes/${scheme.slug}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error();
      setStatus({ type: "success", text: `Deleted "${scheme.scheme_name}". Remember to reindex.` });
      fetchSchemes();
    } catch {
      setStatus({ type: "error", text: "Delete failed." });
    }
  }

  function handleSaved(verb) {
    setFormState(null);
    setStatus({ type: "success", text: `Scheme ${verb}. Remember to reindex so it shows up in chat/eligibility.` });
    fetchSchemes();
  }

  async function handleUpload(e, kind) {
    const file = e.target.files[0];
    e.target.value = ""; // allow re-selecting the same file later
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${BASE_URL}/admin/upload/${kind}`, {
        method: "POST",
        body: formData,
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Upload failed.");
      setStatus({
        type: "success",
        text: kind === "csv" ? `CSV replaced (${body.rows} rows). Remember to reindex.` : `PDF "${body.filename}" added. Remember to reindex.`,
      });
      fetchSchemes();
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    }
  }

  async function handleReindex() {
    setReindexing(true);
    setStatus(null);
    try {
      const res = await fetch(`${BASE_URL}/admin/reindex`, { method: "POST" });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Reindex failed.");
      setStatus({
        type: "success",
        text: `Reindexed: ${body.documents} documents, ${body.chunks} chunks. Chat and eligibility now reflect your changes.`,
      });
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    } finally {
      setReindexing(false);
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-topbar">
        <div className="admin-topbar__title">SchemeSetu — Admin</div>
        <div className="admin-topbar__actions">
          <a href="/" className="admin-btn admin-btn--ghost">
            ← Back to chat
          </a>
        </div>
      </div>

      {status && (
        <div className={`admin-banner admin-banner--${status.type}`}>
          {status.text}
          <button className="admin-banner__close" onClick={() => setStatus(null)} aria-label="Dismiss">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="admin-tabs" role="tablist">
        <button
          role="tab"
          aria-selected={view === "schemes"}
          className={"admin-tab" + (view === "schemes" ? " admin-tab--active" : "")}
          onClick={() => setView("schemes")}
        >
          Schemes
        </button>
        <button
          role="tab"
          aria-selected={view === "gaps"}
          className={"admin-tab" + (view === "gaps" ? " admin-tab--active" : "")}
          onClick={() => setView("gaps")}
        >
          Unanswered questions
        </button>
      </div>

      {view === "gaps" && (
        <GapsPanel
          onCreate={(g) => setFormState({ mode: "create", hint: { question: g.question, count: g.count } })}
        />
      )}

      {view === "schemes" && (
        <>
      <div className="admin-toolbar">
        <div className="admin-search">
          <Search size={15} />
          <input
            placeholder="Search by scheme name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <button className="admin-btn admin-btn--primary" onClick={() => setFormState({ mode: "create" })}>
          <Plus size={15} /> New scheme
        </button>

        <label className="admin-btn admin-btn--ghost">
          <Upload size={14} /> Upload CSV
          <input type="file" accept=".csv" hidden onChange={(e) => handleUpload(e, "csv")} />
        </label>

        <label className="admin-btn admin-btn--ghost">
          <Upload size={14} /> Upload PDF
          <input type="file" accept=".pdf" hidden onChange={(e) => handleUpload(e, "pdf")} />
        </label>

        <button className="admin-btn admin-btn--saffron" onClick={handleReindex} disabled={reindexing}>
          <RefreshCw size={14} className={reindexing ? "admin-spin" : ""} />
          {reindexing ? "Reindexing…" : "Reindex"}
        </button>
      </div>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Scheme</th>
              <th>Level</th>
              <th>Category</th>
              <th>Slug</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {listLoading ? (
              <tr>
                <td colSpan={5} className="admin-table__empty">
                  Loading…
                </td>
              </tr>
            ) : schemes.length === 0 ? (
              <tr>
                <td colSpan={5} className="admin-table__empty">
                  No schemes match.
                </td>
              </tr>
            ) : (
              schemes.map((s) => (
                <tr key={s.slug}>
                  <td className="admin-table__name">{s.scheme_name}</td>
                  <td>
                    <span className={"eligibility-card__badge" + (s.level === "Central" ? " eligibility-card__badge--central" : "")}>
                      {s.level === "Central" ? <Landmark size={11} /> : <MapPin size={11} />}
                      {s.level}
                    </span>
                  </td>
                  <td className="admin-table__muted">{s.schemeCategory}</td>
                  <td className="admin-table__muted">{s.slug}</td>
                  <td className="admin-table__actions">
                    <button className="admin-icon-btn" onClick={() => setFormState({ mode: "edit", scheme: s })} aria-label="Edit">
                      <Pencil size={14} />
                    </button>
                    <button className="admin-icon-btn admin-icon-btn--danger" onClick={() => handleDelete(s)} aria-label="Delete">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="admin-pagination">
        <span>
          {total} scheme{total !== 1 ? "s" : ""} · page {page} of {totalPages}
        </span>
        <div className="admin-pagination__controls">
          <button className="admin-icon-btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            <ChevronLeft size={16} />
          </button>
          <button className="admin-icon-btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

        </>
      )}

      {formState && (
        <SchemeForm
          mode={formState.mode}
          initial={formState.mode === "edit" ? formState.scheme : EMPTY_FORM}
          hint={formState.hint}
          onCancel={() => setFormState(null)}
          onSaved={() => handleSaved(formState.mode === "edit" ? "updated" : "created")}
        />
      )}
    </div>
  );
}
