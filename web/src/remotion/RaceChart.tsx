// Title race / relegation battle: each team's chance after every matchweek,
// drawn left to right over time. The four teams with the highest latest
// chance get a brand colour and a moving label; any others are faint context.
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { chance } from "../lib/format";
import { bodyFont, displayFont, PL, SERIES } from "../lib/theme";

// Label text colours: same as the lines, but a lighter pink so it stays
// readable on purple.
const LABEL = [PL.green, PL.cyan, "#FF5C95", PL.white];

export interface RaceProps {
  title: string;
  rounds: number[];
  teams: { team: string; values: number[] }[];
}

export const RACE_FPS = 30;
export const RACE_DURATION = 150;
const DRAW_START = 18;
const DRAW_FRAMES = 90;

export const RaceChart: React.FC<RaceProps> = ({ title, rounds, teams }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const M = { l: 84, r: 236, t: 110, b: 64 };
  const plotW = width - M.l - M.r;
  const plotH = height - M.t - M.b;
  const last = rounds.length - 1;
  const x = (i: number) => M.l + (last === 0 ? plotW : (i / last) * plotW);
  const y = (v: number) => M.t + (1 - v) * plotH;

  // How far along the matchweeks the lines have been drawn (fractional).
  const progress = interpolate(frame, [DRAW_START, DRAW_START + DRAW_FRAMES], [0, last], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.45, 0, 0.2, 1),
  });
  const valueAt = (values: number[], p: number) => {
    const i = Math.min(Math.floor(p), last);
    const t = p - i;
    return i >= last ? values[last] : values[i] + (values[i + 1] - values[i]) * t;
  };

  const ranked = [...teams].sort((a, b) => b.values[last] - a.values[last]);
  const coloured = ranked.slice(0, SERIES.length);
  const context = ranked.slice(SERIES.length);

  // Moving labels at each line's tip, nudged apart so they never overlap.
  const tips = coloured
    .map((t, k) => ({ ...t, k, v: valueAt(t.values, progress) }))
    .sort((a, b) => b.v - a.v);
  let previousY = -Infinity;
  const labelY = new Map<string, number>();
  for (const tip of tips) {
    const wanted = y(tip.v);
    const placed = Math.max(wanted, previousY + 36);
    labelY.set(tip.team, placed);
    previousY = placed;
  }

  const path = (values: number[]) => {
    const whole = Math.floor(progress);
    const pts = values.slice(0, whole + 1).map((v, i) => `${x(i)},${y(v)}`);
    if (progress > whole && whole < last) pts.push(`${x(progress)},${y(valueAt(values, progress))}`);
    return pts.join(" ");
  };

  const fadeIn = interpolate(frame, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: PL.purple, fontFamily: bodyFont, color: PL.white }}>
      <div
        style={{
          position: "absolute",
          left: M.l,
          top: 34,
          fontFamily: displayFont,
          fontWeight: 800,
          fontSize: 46,
          letterSpacing: "0.02em",
          textTransform: "uppercase",
          opacity: fadeIn,
          translate: interpolate(frame, [0, 16], ["0px 16px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        {title}
      </div>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0, opacity: fadeIn }}>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={M.l} x2={M.l + plotW} y1={y(v)} y2={y(v)} stroke="rgba(255,255,255,0.12)" strokeWidth={1.5} />
            <text x={M.l - 16} y={y(v) + 8} textAnchor="end" fill="rgba(255,255,255,0.6)" fontSize={24}>
              {v * 100}%
            </text>
          </g>
        ))}
        {rounds.map((r, i) => (
          <text key={r} x={x(i)} y={height - 28} textAnchor="middle" fill="rgba(255,255,255,0.6)" fontSize={24}>
            MW{r}
          </text>
        ))}
        {context.map((t) => (
          <polyline key={t.team} points={path(t.values)} fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth={3} strokeLinejoin="round" />
        ))}
        {coloured.map((t, k) => (
          <polyline
            key={t.team}
            points={path(t.values)}
            fill="none"
            stroke={SERIES[k]}
            strokeWidth={6}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
        {coloured.map((t, k) => {
          const v = valueAt(t.values, progress);
          const ly = labelY.get(t.team) ?? y(v);
          return (
            <g key={t.team}>
              <circle cx={x(progress)} cy={y(v)} r={10} fill={SERIES[k]} stroke={PL.purple} strokeWidth={4} />
              <line x1={x(progress) + 12} x2={x(progress) + 26} y1={y(v)} y2={ly} stroke={SERIES[k]} strokeWidth={2} />
              <text x={x(progress) + 32} y={ly + 9} fill={PL.white} fontSize={27} fontWeight={600}>
                {t.team} <tspan fill={LABEL[k]} fontWeight={800}>{chance(v)}</tspan>
              </text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
