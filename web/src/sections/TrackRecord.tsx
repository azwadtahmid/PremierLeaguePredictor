import type { SiteData, Summary } from "../lib/data";
import { pct } from "../lib/format";
import { Reveal, useCountUp, useInView } from "../lib/motion";
import { PL } from "../lib/theme";
import { RECORD_DURATION, RECORD_FPS, RecordRace } from "../remotion/RecordRace";
import { ScrollPlayer } from "../remotion/ScrollPlayer";

function Stat({
  label,
  value,
  format,
  sub,
  accent,
  start,
  delay,
}: {
  label: string;
  value: number;
  format: (v: number) => string;
  sub: string;
  accent: "green" | "cyan" | "pink" | "white";
  start: boolean;
  delay: number;
}) {
  const shown = useCountUp(value, start);
  return (
    <Reveal className={`stat stat-${accent}`} delay={delay}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{format(shown)}</span>
      <span className="stat-sub">{sub}</span>
    </Reveal>
  );
}

export function TrackRecord({ data }: { data: SiteData }) {
  const { locked, backtest } = data.track_record;
  const record: Summary | null = locked ?? backtest;
  const [ref, inView] = useInView<HTMLDivElement>(0.3);

  if (!record) return null;
  const note = locked
    ? `Live predictions, locked before kick-off: ${locked.matches} matches scored.` +
      (backtest ? ` The ${backtest.matches} matches before tracking began are a separate backtest (${pct(backtest.accuracy)} right).` : "")
    : `No live prediction has been played yet. Until the first locked results come in, this is a backtest of the ${backtest?.matches} matches already played, using only results from before each match.`;

  return (
    <section className="section section-white" id="record" aria-labelledby="record-title">
      <div className="wrap">
        <Reveal>
          <p className="eyebrow">Honest scoring</p>
          <h2 id="record-title">Track record</h2>
          <p className="section-note">{note}</p>
        </Reveal>
        <div className="stats" ref={ref}>
          <Stat label="Results right" value={record.accuracy} format={(v) => pct(v, 1)} sub={`${record.results_right} of ${record.matches}`} accent="green" start={inView} delay={0} />
          <Stat label="Exact scores" value={record.exact_scores} format={(v) => Math.round(v).toString()} sub={`${pct(record.exact_scores / record.matches, 1)} of matches`} accent="cyan" start={inView} delay={1} />
          <Stat label="Points" value={record.points} format={(v) => Math.round(v).toString()} sub="3 exact score · 1 right result" accent="pink" start={inView} delay={2} />
          <Stat label="Bet365 favourite" value={record.bookmaker_accuracy ?? 0} format={(v) => pct(v, 1)} sub="results right" accent="white" start={inView} delay={3} />
          <Stat label="Always home win" value={record.home_win_accuracy} format={(v) => pct(v, 1)} sub="results right" accent="white" start={inView} delay={4} />
        </div>
        <Reveal className="record-player" delay={2}>
          <ScrollPlayer
            component={RecordRace}
            inputProps={{
              caption: locked ? `Live record · ${locked.matches} matches` : `Backtest · ${record.matches} matches`,
              rows: [
                { name: "This model", value: record.accuracy, colour: PL.green, textColour: PL.purple },
                { name: "Bet365 favourite", value: record.bookmaker_accuracy ?? 0, colour: PL.white, textColour: PL.purple },
                { name: "Always home win", value: record.home_win_accuracy, colour: PL.cyan, textColour: PL.purple },
              ],
            }}
            durationInFrames={RECORD_DURATION}
            fps={RECORD_FPS}
            width={1400}
            height={420}
            mode="once"
            label={`Results right: this model ${pct(record.accuracy, 1)}, Bet365 favourite ${pct(record.bookmaker_accuracy, 1)}, always home win ${pct(record.home_win_accuracy, 1)}`}
          />
        </Reveal>
      </div>
    </section>
  );
}
