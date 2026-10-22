import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { tg } from "./api.js";
import { applyTheme, getTheme } from "./theme.js";
import "./styles.css";

applyTheme(getTheme()); // tanlangan light/night — birinchi chizishdan oldin
tg?.ready();
tg?.expand();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
