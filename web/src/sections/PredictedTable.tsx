import type { SiteData } from "../lib/data";
import { chance } from "../lib/format";
import { Reveal, useInView } from "../lib/motion";

function Change({ value, percent = false, invert = false }: { value?: number; percent?: boolean; invert?: boolean }) {
  if (value == null) return null;
  const shown = percent ? value * 100 : value;
  if (Math.abs(shown) < (percent ? 0.5 : 0.05)) return <span className="delta">no change</span>;
  const better = invert ? value < 0 : value > 0;
  return (
    <span className={`delta ${better ? "up" : "down"}`}>
      {shown > 0 ? "▲ +" : "▼ −"}
      {Math.abs(shown).toFixed(percent ? 0 : 1)}
      {percent ? " pts" : ""}
    </span>
  );
}

function ChanceCell({ value, change, kind }: { value: number; change?: number; kind: "champion" | "top4" | "relegated" }) {
  return (
    <td className={`chance chance-${kind}`}>
      <span className="chance-fill" style={{ "--w": value } as React.CSSProperties} aria-hidden="true" />
      <span className="chance-value">{chance(value)}</span>
      <Change value={change} percent invert={kind === "relegated"} />
    </td>
  );
}

export function PredictedTable({ data }: { data: SiteData }) {
  const pt = data.predicted_table;
  const [ref, inView] = useInView<HTMLTableSectionElement>(0.05);
  if (!pt) return null;
  const n = pt.rows.length;

  return (
    <section className="section section-purple" id="table" aria-labelledby="table-title">
      <div className="wrap">
        <Reveal>
          <p className="eyebrow eyebrow-green">10,000 simulations</p>
          <h2 id="table-title">Predicted final table</h2>
          <p className="section-note">
            After matchweek {pt.after_round}.
            {pt.compared_with ? ` Arrows and changes are since matchweek ${pt.compared_with}; chance changes are in percentage points.` : ""}
          </p>
          <p className="swipe-hint">Swipe the table for title, top 4 and relegation chances →</p>
        </Reveal>
        <div className="table-scroll">
          <table className="ptable">
            <thead>
              <tr>
                <th>Pos</th>
                <th className="left">Team</th>
                <th>Move</th>
                <th>Pts now</th>
                <th>Expected pts</th>
                <th>Champion</th>
                <th>Top 4</th>
                <th>Relegated</th>
              </tr>
            </thead>
            <tbody ref={ref} className={inView ? "rows-in" : ""}>
              {pt.rows.map((r, i) => {
                const c = r.change ?? undefined;
                const zone = r.position <= 4 ? "zone-top" : r.position > n - 3 ? "zone-bottom" : "";
                const move = c?.position ?? 0;
                return (
                  <tr key={r.team} className={zone} style={{ "--i": i } as React.CSSProperties}>
                    <td className="pos">{r.position}</td>
                    <td className="left team">{r.team}</td>
                    <td className={`move ${move > 0 ? "up" : move < 0 ? "down" : ""}`}>
                      {move > 0 ? `▲ ${move}` : move < 0 ? `▼ ${-move}` : "–"}
                    </td>
                    <td>{r.points_now}</td>
                    <td className="xpts">
                      <span>{r.expected_points.toFixed(0)}</span>
                      <Change value={c?.expected_points} />
                    </td>
                    <ChanceCell value={r.champion} change={c?.champion} kind="champion" />
                    <ChanceCell value={r.top_4} change={c?.top_4} kind="top4" />
                    <ChanceCell value={r.relegated} change={c?.relegated} kind="relegated" />
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="zones">
          <span className="z-top">Top 4 · Champions League</span>
          <span className="z-bottom">Relegation</span>
        </div>
      </div>
    </section>
  );
}
