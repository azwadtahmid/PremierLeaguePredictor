export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-stripes" aria-hidden="true">
        <i /><i /><i /><i />
      </div>
      <div className="wrap footer-inner">
        <div>
          <p className="footer-brand">PL Predictor</p>
          <p>Predicted scorelines and a predicted final table for the 2026/27 Premier League, updated every morning.</p>
        </div>
        <div>
          <p>
            Results and odds: <a href="https://www.football-data.co.uk/">football-data.co.uk</a>
            <br />
            Fixtures: <a href="https://fixturedownload.com/">fixturedownload.com</a>
          </p>
          <p>
            <a href="https://github.com/azwadtahmid/PremierLeaguePredictor">Code, models and data on GitHub</a>
          </p>
          <p className="footer-small">Animations built with Remotion. Not affiliated with the Premier League.</p>
        </div>
      </div>
    </footer>
  );
}
