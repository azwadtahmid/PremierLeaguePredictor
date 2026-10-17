import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { bodyFont, displayFont } from "./lib/theme";
import "./styles.css";

// The same Google Fonts the Remotion compositions use, for the whole page.
document.documentElement.style.setProperty("--font-body", `${bodyFont}, system-ui, sans-serif`);
document.documentElement.style.setProperty("--font-display", `${displayFont}, ${bodyFont}, sans-serif`);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
