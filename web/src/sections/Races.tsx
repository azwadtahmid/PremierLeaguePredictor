import type { Race, SiteData } from "../lib/data";
import { chance } from "../lib/format";
import { Reveal, useIsNarrow } from "../lib/motion";
import { RACE_DURATION, RACE_FPS, RaceChart } from "../remotion/RaceChart";
import { ScrollPlayer } from "../remotion/ScrollPlayer";

function RacePanel({ title, race, delay }: { title: string; race: Race | null; delay: number }) {
  const narrow = useIsNarrow();
  return (
    <Reveal className="race" delay={delay}>
      {race && race.rounds.length >= 2 ? (
        <ScrollPlayer
          key={narrow ? "narrow" : "wide"}
          component={RaceChart}
          inputProps={{ title, rounds: race.rounds, teams: race.teams }}
          durationInFrames={RACE_DURATION}
          fps={RACE_FPS}
          width={narrow ? 720 : 960}
          height={narrow ? 620 : 560}
          mode="once"
          label={`${title}, latest: ${race.teams.map((t) => `${t.team} ${chance(t.values.at(-1))}`).join(", ")}`}
        />
      ) : (
        <p className="race-empty">{title} appears after two completed matchweeks.</p>
      )}
    </Reveal>
  );
}

export function Races({ data }: { data: SiteData }) {
  return (
    <section className="section section-deep" id="races" aria-labelledby="races-title">
      <div className="wrap">
        <Reveal>
          <p className="eyebrow eyebrow-cyan">Week by week</p>
          <h2 id="races-title">How the races have moved</h2>
          <p className="section-note">
            Each team's chance after every completed matchweek. The four teams most in the race are
            coloured; anyone else is a faint line.
          </p>
        </Reveal>
        <div className="races">
          <RacePanel title="Title race" race={data.title_race} delay={0} />
          <RacePanel title="Relegation battle" race={data.relegation_race} delay={1} />
        </div>
      </div>
    </section>
  );
}
