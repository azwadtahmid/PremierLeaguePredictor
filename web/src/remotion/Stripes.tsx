// The four accent colours as diagonal bars sweeping across the frame,
// a nod to the Premier League's broadcast graphics.
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { PL } from "../lib/theme";

const BARS = [PL.cyan, PL.pink, PL.white, PL.green];

export const Stripes: React.FC<{ startFrame?: number; exitFrame?: number; opacity?: number }> = ({
  startFrame = 0,
  exitFrame,
  opacity = 1,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const barWidth = Math.max(width, height) * 0.085;

  return (
    <AbsoluteFill style={{ overflow: "hidden", opacity }}>
      <div
        style={{
          position: "absolute",
          right: -barWidth * 1.5,
          top: -height * 0.4,
          height: height * 1.8,
          display: "flex",
          gap: barWidth * 0.18,
          rotate: "18deg",
        }}
      >
        {BARS.map((colour, i) => (
          <div
            key={colour}
            style={{
              width: barWidth,
              height: "100%",
              background: colour,
              translate: interpolate(
                frame,
                exitFrame == null
                  ? [startFrame + i * 4, startFrame + i * 4 + 0.7 * fps]
                  : [startFrame + i * 4, startFrame + i * 4 + 0.7 * fps, exitFrame + i * 3, exitFrame + i * 3 + 0.5 * fps],
                exitFrame == null
                  ? [`0px ${height * 1.6}px`, "0px 0px"]
                  : [`0px ${height * 1.6}px`, "0px 0px", "0px 0px", `0px ${-height * 1.6}px`],
                {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                },
              ),
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};
