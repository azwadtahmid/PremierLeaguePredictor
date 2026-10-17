import type { SiteData } from "../lib/data";
import { pct } from "../lib/format";
import { Reveal } from "../lib/motion";

const STEPS = [
  {
    n: "01",
    title: "Scorelines",
    text: "A goals model gives every team an attack and a defence rating, learned from past results with recent matches counting more. From those it estimates each side's expected goals, then the chance of every scoreline. The predicted score is the most likely scoreline for the most likely result.",
  },
  {
    n: "02",
    title: "Predicted table",
    text: "After every matchweek the rest of the season is played out 10,000 times with random scores drawn from the goals model. Counting where each team finishes gives its chance of the title, the top 4 and relegation. These chances are probably too confident, because team strengths are treated as fixed.",
  },
  {
    n: "03",
    title: "Honest scoring",
    text: "Each prediction is locked about 48 hours before kick-off and never edited. A right result scores 1 point, an exact score 3. The benchmarks are \"always pick the home team\" and the Bet365 favourite.",
  },
  {
    n: "04",
    title: "Tested before use",
    text: "Every model was tested on the whole 2025/26 season, which none of them saw while being built.",
  },
];

export function HowItWorks({ data }: { data: SiteData }) {
  return (
    <section className="section section-white" id="how" aria-labelledby="how-title">
      <div className="wrap">
        <Reveal>
          <p className="eyebrow">Under the hood</p>
          <h2 id="how-title">How it works</h2>
        </Reveal>
        <div className="steps">
          {STEPS.map((s, i) => (
            <Reveal className="step" key={s.n} delay={i}>
              <span className="step-n">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </Reveal>
          ))}
        </div>
        {data.test_metrics && (
          <Reveal className="table-scroll light metrics" delay={1}>
            <table className="ltable">
              <caption>2025/26 test season (366 matches)</caption>
              <thead>
                <tr>
                  <th className="left">Model</th>
                  <th>Results right</th>
                  <th>Log loss (lower is better)</th>
                  <th>Exact scores</th>
                </tr>
              </thead>
              <tbody>
                {data.test_metrics.map((m) => (
                  <tr key={m.model} className={m.model.startsWith("Goals") ? "row-highlight" : ""}>
                    <td className="left team">{m.model}</td>
                    <td>{pct(m.accuracy, 1)}</td>
                    <td>{m.log_loss.toFixed(3)}</td>
                    <td>{m.exact_score == null ? "–" : pct(m.exact_score, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Reveal>
        )}
      </div>
    </section>
  );
}
