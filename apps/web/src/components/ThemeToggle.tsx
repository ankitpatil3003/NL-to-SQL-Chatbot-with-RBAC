"use client";

// System -> light -> dark. The current theme *is* the <html data-theme> attribute (set before
// first paint by the root layout from localStorage), so it's read as an external store rather
// than mirrored into React state.

import { useSyncExternalStore } from "react";

import { MonitorIcon, MoonIcon, SunIcon } from "./icons";

type Theme = "system" | "light" | "dark";
const ORDER: Theme[] = ["system", "light", "dark"];

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

function currentTheme(): Theme {
  const t = document.documentElement.dataset.theme;
  return t === "light" || t === "dark" ? t : "system";
}

function apply(theme: Theme) {
  if (theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
  try {
    if (theme === "system") localStorage.removeItem("theme");
    else localStorage.setItem("theme", theme);
  } catch {
    /* storage unavailable: the choice lasts for this page only */
  }
}

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, currentTheme, () => "system" as Theme);
  const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
  const Icon = theme === "light" ? SunIcon : theme === "dark" ? MoonIcon : MonitorIcon;
  return (
    <button
      onClick={() => apply(next)}
      title={`Theme: ${theme} (switch to ${next})`}
      className="rounded-md p-1.5 text-fg-secondary hover:bg-bg-muted hover:text-fg"
    >
      <Icon />
    </button>
  );
}
