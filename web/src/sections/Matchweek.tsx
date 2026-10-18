import { useEffect, useMemo, useRef, useState } from "react";
import type { Fixture, Round, SiteData } from "../lib/data";
import { dash, pct, RESULT_NAME, ukDate } from "../lib/format";
import { Reveal } from "../lib/motion";

const TAG = {
  locked: ["Locked", "made before kick-off, never changed"],
  provisional: ["Provisional", "refreshed daily, locks about 24 hours before kick-off"],
  backtest: ["Backtest", "before live tracking began, using only earlier results"],
} as const;

function startingRound(data: SiteData) {
  const fromHash = Number(new URLSearchParams(location.hash.slice(1)).get("mw"));
  if (data.rounds.some((r) => r.round === fromHash)) return fromHash;
  return data.next_round ?? data.latest_completed_round ?? data.rounds[0].round;
}

function ProbBar({ probs }: { probs: Fixture["prediction"]["probs"] }) {
  return (
    <div className="probs">
      <div className="prob-bar" role="img" aria-label={`Home win ${pct(probs.H)}, draw ${pct(probs.D)}, away win ${pct(probs.A)}`}>
        <span className="h" style={{ "--w": probs.H } as React.CSSProperties} />
        <span className="d" style={{ "--w": probs.D } as React.CSSProperties} />
        <span className="a" style={{ "--w": probs.A } as React.CSSProperties} />
      </div>
      <div className="prob-nums">
        <span><i className="key key-h" />Home {pct(probs.H)}</span>
        <span><i className="key key-d" />Draw {pct(probs.D)}</span>
        <span><i className="key key-a" />Away {pct(probs.A)}</span>
      </div>
    </div>
  );
}

function FixtureCard({ fixture: f, index }: { fixture: Fixture; index: number }) {
  const p = f.prediction;
  const played = f.status === "played";
  const verdict = !played ? null : f.correct_score ? "exact" : f.correct_result ? "result" : "wrong";
  const verdictText = { exact: "✓ Exact score · +3", result: "✓ Right result · +1", wrong: "✗ Wrong · 0" };
  const time = f.status === "postponed" ? "Postponed" : ukDate(f.kickoff, { hour: "2-digit", minute: "2-digit" });

  return (
    // "verdict-…" (not "fx-…"): .fx-result is the score bar inside the card.
    <article className={`fixture ${verdict ? `verdict-${verdict}` : ""}`} style={{ "--i": index } as React.CSSProperties}>
      <div className="fx-top">
        <span className="fx-time">{time}</span>
        <span className={`tag tag-${p.source}`}>{TAG[p.source][0]}</span>
      </div>
      <div className="fx-main">
        <span className="fx-team fx-home" title={f.home}>{f.home}</span>
        <div className="fx-pred">
          <span className="fx-pred-label">Predicted</span>
          <span className="fx-score">{dash(p.score)}</span>
        </div>
        <span className="fx-team fx-away" title={f.away}>{f.away}</span>
      </div>
      {played && f.score && (
        <div className={`fx-result fx-result-${verdict}`}>
          <span>Final <strong>{dash(f.score)}</strong></span>
          <span className="fx-verdict">{verdictText[verdict!]}</span>
        </div>
      )}
      {played && f.result_source === "fixturedownload" && (
        <p className="fx-early">Early score from fixturedownload.com · Bet365 odds and full stats to follow</p>
      )}
      <ProbBar probs={p.probs} />
      <p className="fx-detail">
        Likely: {p.likely}
        <span className="fx-xg">
          {" "}· xG {p.xg[0].toFixed(2)}–{p.xg[1].toFixed(2)}
          {f.bookmaker_pick ? ` · Bet365: ${RESULT_NAME[f.bookmaker_pick].toLowerCase()}` : ""}
        </span>
      </p>
    </article>
  );
}

function RoundSummary({ round }: { round: Round }) {
  const s = round.summary;
  if (!s) return null;
  const chips: [string, string][] = [
    [`${s.results_right}/${s.matches}`, "results right"],
    [String(s.exact_scores), "exact scores"],
    [String(s.points), "points"],
  ];
  if (s.bookmaker_accuracy != null) chips.push([`${Math.round(s.bookmaker_accuracy * s.matches)}/${s.matches}`, "Bet365 favourite"]);
  chips.push([`${Math.round(s.home_win_accuracy * s.matches)}/${s.matches}`, "always home"]);
  return (
    <div className="mw-summary" key={round.round}>
      {chips.map(([value, label], i) => (
        <span className="chip" key={label} style={{ "--i": i } as React.CSSProperties}>
          <strong>{value}</strong> {label}
        </span>
      ))}
    </div>
  );
}

export function Matchweek({ data }: { data: SiteData }) {
  const [current, setCurrent] = useState(() => startingRound(data));
  const round = data.rounds.find((r) => r.round === current)!;
  const stripRef = useRef<HTMLDivElement>(null);
  const first = data.rounds[0].round;
  const last = data.rounds[data.rounds.length - 1].round;

  useEffect(() => {
    history.replaceState(null, "", `#mw=${current}`);
    // Centre the selected pill by scrolling the strip sideways only
    // (scrollIntoView would also scroll the whole page).
    const strip = stripRef.current;
    const pill = strip?.querySelector<HTMLElement>(`[data-round="${current}"]`);
    if (strip && pill) {
      strip.scrollTo({ left: pill.offsetLeft - strip.clientWidth / 2 + pill.clientWidth / 2, behavior: "smooth" });
    }
  }, [current]);

  const days = useMemo(() => {
    const groups = new Map<string, Fixture[]>();
    for (const f of round.fixtures) {
      const day = ukDate(f.kickoff, { weekday: "long", day: "numeric", month: "long" });
      groups.set(day, [...(groups.get(day) ?? []), f]);
    }
    return [...groups];
  }, [round]);

  const state = { complete: "Played", "in progress": "In progress", upcoming: "Upcoming" }[round.state];
  let index = 0;

  return (
    <section className="section section-lilac" id="matchweek" aria-labelledby="mw-title">
      <div className="wrap">
        <Reveal>
          <p className="eyebrow">Fixtures and results</p>
          <div className="mw-head">
            <h2 id="mw-title">
              Matchweek <span className="mw-number" key={current}>{current}</span>
            </h2>
            <div className="mw-arrows">
              <button type="button" onClick={() => setCurrent(current - 1)} disabled={current === first} aria-label="Previous matchweek">‹</button>
              <button type="button" onClick={() => setCurrent(current + 1)} disabled={current === last} aria-label="Next matchweek">›</button>
            </div>
          </div>
          <p className="section-note">{state} · kick-off times are UK time</p>
        </Reveal>

        <div className="mw-strip" ref={stripRef} role="tablist" aria-label="Matchweeks">
          {data.rounds.map((r) => (
            <button
              type="button"
              role="tab"
              key={r.round}
              data-round={r.round}
              aria-selected={r.round === current}
              className={`mw-pill mw-${r.state.replace(" ", "-")} ${r.round === data.next_round ? "mw-next" : ""}`}
              onClick={() => setCurrent(r.round)}
            >
              {r.round}
            </button>
          ))}
        </div>

        <RoundSummary round={round} />
        <ul className="legend">
          {Object.entries(TAG).map(([key, [label, text]]) => (
            <li key={key}><span className={`tag tag-${key}`}>{label}</span> {text}</li>
          ))}
        </ul>

        <div className="mw-days" key={current}>
          {days.map(([day, fixtures]) => (
            <div className="mw-day" key={day}>
              <h3>{day}</h3>
              <div className="fixtures">
                {fixtures.map((f) => (
                  <FixtureCard fixture={f} index={index++} key={`${f.home}-${f.away}`} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
