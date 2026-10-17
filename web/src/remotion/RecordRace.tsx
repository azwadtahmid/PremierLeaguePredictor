// Track record as a race: the model's share of results right against the
// Bet365 favourite and "always home", bars growing with counting numbers.
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { bodyFont, displayFont, PL } from "../lib/theme";

export interface RecordProps {
  caption: string;
  rows: { name: string; value: number; colour: string; textColour: string }[];
}

export const RECORD_FPS = 30;
export const RECORD_DURATION = 120;

export const RecordRace: React.FC<RecordProps> = ({ caption, rows }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const max = Math.max(0.6, ...rows.map((r) => r.value));
  const labelW = 300;
  const trackW = width - labelW - 160;

  return (
    <AbsoluteFill style={{ background: PL.purple, color: PL.white, fontFamily: bodyFont, padding: "46px 60px" }}>
      <div
        style={{
          fontSize: 24,
          fontWeight: 600,
          letterSpacing: "0.14em",
          color: PL.cyan,
          opacity: interpolate(frame, [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}
      >
        {caption.toUpperCase()}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 30, marginTop: 34 }}>
        {rows.map((row, i) => {
          const start = 10 + i * 8;
          const grown = interpolate(frame, [start, start + 1.4 * fps], [0, row.value], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          });
          return (
            <div key={row.name} style={{ display: "flex", alignItems: "center" }}>
              <div style={{ width: labelW, fontSize: 30, fontWeight: 600 }}>{row.name}</div>
              <div style={{ width: trackW, height: 52, background: "rgba(255,255,255,0.1)", borderRadius: 10 }}>
                <div
                  style={{
                    width: `${(grown / max) * 100}%`,
                    height: "100%",
                    borderRadius: 10,
                    background: row.colour,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "flex-end",
                    paddingRight: 14,
                    boxSizing: "border-box",
                  }}
                >
                  <span style={{ fontFamily: displayFont, fontWeight: 800, fontSize: 36, color: row.textColour }}>
                    {(grown * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
