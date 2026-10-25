import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";
import { applyTheme, getInitialTheme } from "./theme";

// Set the theme before the first paint so there is no light flash in dark mode.
applyTheme(getInitialTheme());
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
