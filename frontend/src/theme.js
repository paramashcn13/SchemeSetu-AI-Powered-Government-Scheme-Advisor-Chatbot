/* Light / dark theme. The choice is kept in localStorage; with no saved choice
   the device setting (prefers-color-scheme) decides. Applied as
   <html data-theme="light|dark">, which index.css reads. */

const KEY = "ss_theme";

export function getInitialTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* storage blocked: fall through to the device setting */
  }
  const prefersDark =
    typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

export function applyTheme(theme, remember = false) {
  document.documentElement.setAttribute("data-theme", theme);
  if (remember) {
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* ignore */
    }
  }
}
