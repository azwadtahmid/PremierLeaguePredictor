import type { SiteData } from "../lib/data";
import { Reveal, useInView } from "../lib/motion";

export function CurrentTable({ data }: { data: SiteData }) {
  const [ref, inView] = useInView<HTMLTableSectionElement>(0.05);
  const n = data.table.length;
  return (
    <section className="section section-white" id="standings" aria-labelledby="standings-title">
      <div className="wrap">
        <Reveal>
          <p className="eyebrow">The real thing</p>
          <h2 id="standings-title">Current table</h2>
        </Reveal>
        <div className="table-scroll light">
          <table className="ltable">
            <thead>
              <tr>
                <th>Pos</th>
                <th className="left">Team</th>
                {["P", "W", "D", "L", "GF", "GA", "GD", "Pts"].map((h) => <th key={h}>{h}</th>)}
              </tr>
            </thead>
            <tbody ref={ref} className={inView ? "rows-in" : ""}>
              {data.table.map((r, i) => (
                <tr key={r.team} className={i < 4 ? "zone-top" : i >= n - 3 ? "zone-bottom" : ""} style={{ "--i": i } as React.CSSProperties}>
                  <td className="pos">{i + 1}</td>
                  <td className="left team">{r.team}</td>
                  <td>{r.played}</td>
                  <td>{r.won}</td>
                  <td>{r.drawn}</td>
                  <td>{r.lost}</td>
                  <td>{r.gf}</td>
                  <td>{r.ga}</td>
                  <td>{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
                  <td className="pts">{r.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
