/** Canonical theme palette. The build generates CSS from these same tokens. */
export const themes = Object.freeze({
  light: Object.freeze({ label: "Light", scheme: "light", background: "#f6f7f9", surface: "#ffffff", raised: "#edf1f4", text: "#17252e", muted: "#4d606c", accent: "#146255", onAccent: "#ffffff", border: "#71818a", focus: "#075fc7" }),
  dark: Object.freeze({ label: "Dark", scheme: "dark", background: "#11191d", surface: "#1a252b", raised: "#24343c", text: "#edf3f5", muted: "#b7c6ce", accent: "#a4dfc7", onAccent: "#10271f", border: "#82949e", focus: "#ffd166" }),
  sepia: Object.freeze({ label: "Sepia", scheme: "light", background: "#f3ecdf", surface: "#fffaf0", raised: "#ebe0cb", text: "#332b21", muted: "#665744", accent: "#705025", onAccent: "#ffffff", border: "#8f7c63", focus: "#075bb0" }),
  contrast: Object.freeze({ label: "High contrast", scheme: "dark", background: "#000000", surface: "#000000", raised: "#171717", text: "#ffffff", muted: "#eeeeee", accent: "#ffff00", onAccent: "#000000", border: "#ffffff", focus: "#00ffff" }),
  calm: Object.freeze({ label: "Calm", scheme: "light", background: "#edf2ed", surface: "#f9fcf7", raised: "#e0e9df", text: "#23372c", muted: "#4e6456", accent: "#2f624a", onAccent: "#ffffff", border: "#718574", focus: "#075bb0" }),
});

export const fontStacks = Object.freeze({
  system: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  atkinson: '"AK Atkinson", system-ui, sans-serif',
  noto: '"AK Noto Sans", system-ui, sans-serif',
});
