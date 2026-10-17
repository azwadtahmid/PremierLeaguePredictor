import { useEffect, useState } from "react";
import { loadData, type SiteData } from "./lib/data";
import { CurrentTable } from "./sections/CurrentTable";
import { Footer } from "./sections/Footer";
import { Hero } from "./sections/Hero";
import { HowItWorks } from "./sections/HowItWorks";
import { Matchweek } from "./sections/Matchweek";
import { Nav } from "./sections/Nav";
import { PredictedTable } from "./sections/PredictedTable";
import { Races } from "./sections/Races";
import { TrackRecord } from "./sections/TrackRecord";

export function App() {
  const [data, setData] = useState<SiteData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    loadData().then(setData).catch(() => setError(true));
  }, []);

  if (error) {
    return <p className="status">Couldn't load the predictions. Try refreshing the page.</p>;
  }
  if (!data) {
    return (
      <div className="status loading" role="status">
        <span className="loader" aria-hidden="true"><i /><i /><i /><i /></span>
        Loading predictions…
      </div>
    );
  }

  return (
    <>
      <a className="skip" href="#matchweek">Skip to predictions</a>
      <Nav />
      <main>
        <Hero data={data} />
        <Matchweek data={data} />
        <PredictedTable data={data} />
        <Races data={data} />
        <TrackRecord data={data} />
        <CurrentTable data={data} />
        <HowItWorks data={data} />
      </main>
      <Footer />
    </>
  );
}
