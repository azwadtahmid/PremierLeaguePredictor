import { useEffect, useState } from "react";
import { useScrollProgress } from "../lib/motion";

const LINKS = [
  ["matchweek", "Matchweek"],
  ["table", "Predicted table"],
  ["races", "Races"],
  ["record", "Track record"],
  ["how", "How it works"],
] as const;

export function Nav() {
  const progress = useScrollProgress();
  const [solid, setSolid] = useState(false);
  useEffect(() => {
    const update = () => setSolid(window.scrollY > 40);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);

  return (
    <header className={`nav ${solid ? "nav-solid" : ""}`}>
      <div className="wrap nav-row">
        <a className="brand" href="#top" aria-label="Premier League Predictor, back to top">
          <span className="brand-mark" aria-hidden="true">
            <i /><i /><i /><i />
          </span>
          <span className="brand-name">PL Predictor</span>
        </a>
        <nav aria-label="Sections">
          <ul className="nav-links">
            {LINKS.map(([id, label]) => (
              <li key={id}>
                <a href={`#${id}`}>{label}</a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="progress" aria-hidden="true">
        <span style={{ scale: `${progress} 1` }} />
      </div>
    </header>
  );
}
