import { useMemo } from "react";
import type { SiteData } from "../lib/data";
import { ukDate } from "../lib/format";
import { useIsNarrow } from "../lib/motion";
import { FPS, HeroReel, heroDuration, type HeroProps } from "../remotion/HeroReel";
import { ScrollPlayer } from "../remotion/ScrollPlayer";

export function Hero({ data }: { data: SiteData }) {
  const narrow = useIsNarrow();

  const props = useMemo<HeroProps>(() => {
    const round = data.rounds.find((r) => r.round === data.next_round) ?? null;
    const fixtures = (round?.fixtures ?? [])
      .filter((f) => f.status !== "played")
      .map((f) => ({
        home: f.home,
        away: f.away,
        score: f.prediction.score,
        ...f.prediction.probs,
        likely: f.prediction.likely,
        when: ukDate(f.kickoff, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }),
      }));
    const top = data.predicted_table?.rows.reduce((a, b) => (b.champion > a.champion ? b : a));
    return {
      season: data.season,
      round: round?.round ?? null,
      fixtures,
      favourite: top && data.predicted_table
        ? { team: top.team, champion: top.champion, afterRound: data.predicted_table.after_round }
        : null,
    };
  }, [data]);

  const duration = heroDuration(props.fixtures.length, props.favourite != null);
  const updated = ukDate(data.updated, { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });

  return (
    <section className="hero" id="top" aria-labelledby="hero-title">
      <div className="wrap hero-inner">
        <h1 id="hero-title" className="sr-only">Premier League Predictor {data.season}</h1>
        <ScrollPlayer
          key={narrow ? "portrait" : "landscape"}
          component={HeroReel}
          inputProps={props}
          durationInFrames={duration}
          fps={FPS}
          width={narrow ? 1080 : 1920}
          height={narrow ? 1350 : 840}
          mode="loop"
          label={`Animated reel of predicted scores for matchweek ${props.round ?? ""}`}
        />
        <div className="hero-meta">
          <p className="hero-lede">
            Predicted scorelines for every fixture and a predicted final table, checked against
            real results after every matchweek.
          </p>
          <div className="hero-actions">
            <a className="btn btn-green" href="#matchweek">
              {props.round ? `Matchweek ${props.round} predictions` : "Matchweeks"}
            </a>
            <a className="btn btn-ghost" href="#table">Predicted table</a>
          </div>
          <p className="hero-updated">
            <span className="live-dot" aria-hidden="true" /> Updated {updated} UK time · refreshed every morning
          </p>
        </div>
      </div>
    </section>
  );
}
