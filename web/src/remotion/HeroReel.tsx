// Hero animation: intro, then one scene per fixture of the next matchweek
// (predicted score, chances, likely scorelines), then the title favourite.
// Driven entirely by data.json via props, so it updates every day.
import { linearTiming, springTiming, TransitionSeries, type TransitionPresentation } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { bodyFont, displayFont, PL, RESULT_COLOUR } from "../lib/theme";
import { Stripes } from "./Stripes";

export interface HeroFixture {
  home: string;
  away: string;
  score: string;
  H: number;
  D: number;
  A: number;
  likely: string;
  when: string;
}

export interface HeroProps {
  season: string;
  round: number | null;
  fixtures: HeroFixture[];
  favourite: { team: string; champion: number; afterRound: number } | null;
}

export const FPS = 30;
const INTRO = 90;
const FIXTURE = 84;
const OUTRO = 105;
const TRANSITION = 18;

export const heroDuration = (fixtureCount: number, hasOutro: boolean) => {
  const scenes = 1 + fixtureCount + (hasOutro ? 1 : 0);
  return INTRO + fixtureCount * FIXTURE + (hasOutro ? OUTRO : 0) - (scenes - 1) * TRANSITION;
};

const ease = Easing.bezier(0.16, 1, 0.3, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const usePortrait = () => {
  const { width, height } = useVideoConfig();
  return height > width * 0.8;
};

const Intro: React.FC<{ season: string; round: number | null }> = ({ season, round }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const portrait = usePortrait();
  const big = portrait ? width * 0.15 : width * 0.085;

  return (
    <AbsoluteFill style={{ background: PL.purple }}>
      <Stripes startFrame={4} opacity={portrait ? 0.35 : 1} />
      <AbsoluteFill
        style={{
          justifyContent: portrait ? "flex-end" : "center",
          padding: portrait ? `0 ${width * 0.07}px ${width * 0.16}px` : `0 ${width * 0.06}px`,
          fontFamily: displayFont,
          color: PL.white,
        }}
      >
        <div
          style={{
            fontFamily: bodyFont,
            fontWeight: 600,
            fontSize: big * 0.22,
            letterSpacing: "0.18em",
            color: PL.green,
            opacity: interpolate(frame, [8, 8 + 0.5 * fps], [0, 1], clamp),
            translate: interpolate(frame, [8, 8 + 0.5 * fps], ["0px 20px", "0px 0px"], { ...clamp, easing: ease }),
          }}
        >
          {season} SEASON
        </div>
        {["PREMIER LEAGUE", "PREDICTOR"].map((line, i) => (
          <div key={line} style={{ overflow: "hidden", lineHeight: 0.92 }}>
            <div
              style={{
                fontSize: big,
                fontWeight: 800,
                color: i === 1 ? PL.green : PL.white,
                translate: interpolate(frame, [14 + i * 7, 14 + i * 7 + 0.7 * fps], [`0px ${big * 1.1}px`, "0px 0px"], {
                  ...clamp,
                  easing: ease,
                }),
              }}
            >
              {line}
            </div>
          </div>
        ))}
        <div
          style={{
            marginTop: big * 0.3,
            alignSelf: "flex-start",
            fontFamily: bodyFont,
            fontWeight: 600,
            fontSize: big * 0.24,
            color: PL.purple,
            background: PL.white,
            padding: `${big * 0.08}px ${big * 0.22}px`,
            borderRadius: big,
            opacity: interpolate(frame, [36, 36 + 0.4 * fps], [0, 1], clamp),
            scale: interpolate(frame, [36, 36 + 0.5 * fps], [0.8, 1], { ...clamp, easing: ease, output: "perceptual-scale" }),
          }}
        >
          {round ? `Matchweek ${round} predictions` : "Season predictions"}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const FixtureScene: React.FC<{ fixture: HeroFixture; index: number; total: number; round: number | null }> = ({
  fixture,
  index,
  total,
  round,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const portrait = usePortrait();
  const unit = portrait ? width / 100 : height / 100;
  const [homeGoals, awayGoals] = fixture.score.split("-");
  const bars = (["H", "D", "A"] as const).map((key) => ({ key, value: fixture[key] }));
  const grow = interpolate(frame, [22, 22 + 0.9 * fps], [0, 1], { ...clamp, easing: ease });

  const team = (name: string, side: "left" | "right") => (
    <div
      style={{
        flex: 1,
        textAlign: portrait ? "center" : side === "left" ? "right" : "left",
        fontFamily: displayFont,
        fontWeight: 800,
        fontSize: portrait ? unit * 11 : unit * 9.5,
        lineHeight: 1,
        color: PL.white,
        textTransform: "uppercase",
        opacity: interpolate(frame, [4, 4 + 0.4 * fps], [0, 1], clamp),
        translate: interpolate(
          frame,
          [4, 4 + 0.6 * fps],
          [portrait ? "0px 30px" : `${side === "left" ? -60 : 60}px 0px`, "0px 0px"],
          { ...clamp, easing: ease },
        ),
      }}
    >
      {name}
    </div>
  );

  return (
    <AbsoluteFill style={{ background: PL.purple, fontFamily: bodyFont, color: PL.white }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 120%, ${PL.purpleSoft} 0%, ${PL.purple} 60%)`,
        }}
      />
      <AbsoluteFill
        style={{
          padding: portrait ? `${unit * 10}px ${unit * 6}px` : `${unit * 7}px ${unit * 9}px`,
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: unit * (portrait ? 3.6 : 3), fontWeight: 600 }}>
          <span style={{ color: PL.cyan, letterSpacing: "0.12em" }}>
            {round ? `MATCHWEEK ${round}` : "NEXT UP"} · {fixture.when.toUpperCase()}
          </span>
          <span style={{ opacity: 0.6 }}>
            {index + 1} / {total}
          </span>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: portrait ? "column" : "row",
            alignItems: "center",
            gap: unit * (portrait ? 4 : 5),
          }}
        >
          {team(fixture.home, "left")}
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontSize: unit * (portrait ? 3.2 : 2.6),
                fontWeight: 600,
                letterSpacing: "0.2em",
                color: PL.green,
                marginBottom: unit,
                opacity: interpolate(frame, [12, 24], [0, 1], clamp),
              }}
            >
              PREDICTED
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: unit * 2,
                background: PL.white,
                color: PL.purple,
                borderRadius: unit * 2.5,
                padding: `${unit * 0.5}px ${unit * 3.5}px`,
                fontFamily: displayFont,
                fontWeight: 800,
                fontSize: unit * (portrait ? 17 : 15),
                lineHeight: 1.05,
                scale: interpolate(frame, [10, 10 + 0.6 * fps], [0.4, 1], {
                  ...clamp,
                  easing: Easing.spring({ damping: 12 }),
                  output: "perceptual-scale",
                }),
                opacity: interpolate(frame, [10, 16], [0, 1], clamp),
              }}
            >
              <span>{homeGoals}</span>
              <span style={{ color: PL.pink }}>–</span>
              <span>{awayGoals}</span>
            </div>
          </div>
          {team(fixture.away, "right")}
        </div>

        <div>
          <div style={{ display: "flex", height: unit * 2.2, gap: unit * 0.4, borderRadius: unit, overflow: "hidden" }}>
            {bars.map(({ key, value }) => (
              <div
                key={key}
                style={{ width: `${value * 100 * grow}%`, background: RESULT_COLOUR[key], borderRadius: unit * 0.4 }}
              />
            ))}
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: unit * 1.4,
              fontSize: unit * (portrait ? 3.4 : 2.8),
              fontWeight: 600,
            }}
          >
            {bars.map(({ key, value }) => (
              <span key={key} style={{ color: RESULT_COLOUR[key] }}>
                {{ H: "Home", D: "Draw", A: "Away" }[key]} {Math.round(value * 100 * grow)}%
              </span>
            ))}
          </div>
          <div
            style={{
              marginTop: unit * 1.2,
              fontSize: unit * (portrait ? 3.4 : 3),
              opacity: interpolate(frame, [30, 45], [0, 0.8], clamp),
            }}
          >
            Most likely: {fixture.likely.replaceAll(", ", "  ·  ")}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Outro: React.FC<{ favourite: NonNullable<HeroProps["favourite"]> }> = ({ favourite }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const portrait = usePortrait();
  const unit = portrait ? width / 100 : height / 100;
  const shown = interpolate(frame, [12, 12 + 1.2 * fps], [0, favourite.champion * 100], { ...clamp, easing: ease });

  return (
    <AbsoluteFill style={{ background: PL.purple, color: PL.white, fontFamily: bodyFont }}>
      <Stripes startFrame={0} opacity={0.22} />
      <AbsoluteFill style={{ justifyContent: "center", padding: `0 ${portrait ? unit * 7 : unit * 10}px` }}>
        <div style={{ fontSize: unit * (portrait ? 4 : 3.2), fontWeight: 600, letterSpacing: "0.18em", color: PL.cyan }}>
          TITLE FAVOURITE · AFTER MATCHWEEK {favourite.afterRound}
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontWeight: 800,
            fontSize: unit * (portrait ? 18 : 16),
            lineHeight: 1,
            textTransform: "uppercase",
            translate: interpolate(frame, [0, 0.6 * fps], ["0px 40px", "0px 0px"], { ...clamp, easing: ease }),
            opacity: interpolate(frame, [0, 10], [0, 1], clamp),
          }}
        >
          {favourite.team}
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: unit * 2, marginTop: unit }}>
          <span style={{ fontFamily: displayFont, fontWeight: 800, fontSize: unit * (portrait ? 22 : 20), color: PL.green, lineHeight: 1 }}>
            {shown.toFixed(0)}%
          </span>
          <span style={{ fontSize: unit * (portrait ? 4 : 3.2), opacity: 0.8 }}>chance of winning the league</span>
        </div>
        <div style={{ height: unit * 1.6, background: "rgba(255,255,255,0.15)", borderRadius: unit, marginTop: unit * 3 }}>
          <div style={{ width: `${shown}%`, height: "100%", background: PL.green, borderRadius: unit }} />
        </div>
        <div style={{ marginTop: unit * 3, fontSize: unit * (portrait ? 3.2 : 2.6), opacity: interpolate(frame, [40, 60], [0, 0.7], clamp) }}>
          From 10,000 simulations of the rest of the season · updated automatically
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const HeroReel: React.FC<HeroProps> = ({ season, round, fixtures, favourite }) => {
  const { fps } = useVideoConfig();
  // Mixed presentations share one loose type so they can sit in one list.
  const transitions = [
    slide({ direction: "from-right" }),
    wipe({ direction: "from-left" }),
    slide({ direction: "from-bottom" }),
  ] as TransitionPresentation<Record<string, unknown>>[];

  return (
    <AbsoluteFill style={{ background: PL.purple }}>
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={INTRO} premountFor={fps}>
          <Intro season={season} round={round} />
        </TransitionSeries.Sequence>
        {fixtures.flatMap((fixture, i) => [
          <TransitionSeries.Transition
            key={`t-${fixture.home}`}
            presentation={transitions[i % transitions.length]}
            timing={i === 0 ? springTiming({ config: { damping: 200 }, durationInFrames: TRANSITION }) : linearTiming({ durationInFrames: TRANSITION })}
          />,
          <TransitionSeries.Sequence key={`s-${fixture.home}`} durationInFrames={FIXTURE} premountFor={fps}>
            <FixtureScene fixture={fixture} index={i} total={fixtures.length} round={round} />
          </TransitionSeries.Sequence>,
        ])}
        {favourite && (
          <>
            <TransitionSeries.Transition presentation={wipe({ direction: "from-top-left" })} timing={linearTiming({ durationInFrames: TRANSITION })} />
            <TransitionSeries.Sequence durationInFrames={OUTRO} premountFor={fps}>
              <Outro favourite={favourite} />
            </TransitionSeries.Sequence>
          </>
        )}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
