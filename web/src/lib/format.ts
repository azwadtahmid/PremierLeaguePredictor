// Formatting helpers shared by the page and the Remotion compositions.

const UK = "Europe/London";

export const pct = (v: number | null | undefined, digits = 0) =>
  v == null ? "–" : `${(v * 100).toFixed(digits)}%`;

// Chances never round to certainty: 0.9982 shows as ">99%", 0.0004 as "<0.1%".
export const chance = (v: number | null | undefined) => {
  if (v == null) return "–";
  if (v === 0 || v === 1) return pct(v);
  if (v < 0.001) return "<0.1%";
  if (v < 0.01) return pct(v, 1);
  if (v > 0.995) return ">99%";
  return pct(v);
};

export const ukDate = (iso: string, options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: UK, ...options }).format(new Date(iso));

export const RESULT_NAME = { H: "Home win", D: "Draw", A: "Away win" } as const;

export const dash = (score: string) => score.replace("-", " – ");
