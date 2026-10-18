// Shape of docs/data.json, written by src/site.py.

export type Result = "H" | "D" | "A";
export type Source = "locked" | "backtest" | "provisional";

export interface Prediction {
  source: Source;
  locked_at: string | null;
  score: string;
  pick: Result;
  probs: { H: number; D: number; A: number };
  likely: string;
  xg: [number, number];
}

export interface Fixture {
  kickoff: string;
  home: string;
  away: string;
  status: "played" | "upcoming" | "postponed";
  score: string | null;
  result: Result | null;
  prediction: Prediction;
  correct_result: boolean | null;
  correct_score: boolean | null;
  points: number | null;
  bookmaker_pick: Result | null;
  // "fixturedownload" = early score; shots and Bet365 odds still to come.
  result_source: "football-data" | "fixturedownload" | null;
}

export interface Summary {
  matches: number;
  results_right: number;
  exact_scores: number;
  points: number;
  accuracy: number;
  home_win_accuracy: number;
  bookmaker_accuracy: number | null;
}

export interface Round {
  round: number;
  state: "complete" | "in progress" | "upcoming";
  first_kickoff: string;
  source: Source | null;
  summary: Summary | null;
  fixtures: Fixture[];
}

export interface PredictedRow {
  position: number;
  team: string;
  played: number;
  points_now: number;
  expected_points: number;
  champion: number;
  top_4: number;
  relegated: number;
  change: {
    position: number;
    expected_points: number;
    champion: number;
    top_4: number;
    relegated: number;
  } | null;
}

export interface Race {
  rounds: number[];
  teams: { team: string; values: number[] }[];
}

export interface TableRow {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

export interface TestMetric {
  model: string;
  accuracy: number;
  log_loss: number;
  exact_score: number | null;
}

export interface SiteData {
  updated: string;
  season: string;
  next_round: number | null;
  latest_completed_round: number | null;
  track_record: { locked: Summary | null; backtest: Summary | null };
  rounds: Round[];
  predicted_table: {
    after_round: number;
    compared_with: number | null;
    rows: PredictedRow[];
  } | null;
  title_race: Race | null;
  relegation_race: Race | null;
  table: TableRow[];
  test_metrics: TestMetric[] | null;
}

export async function loadData(): Promise<SiteData> {
  const response = await fetch("data.json", { cache: "no-cache" });
  if (!response.ok) throw new Error(`data.json: HTTP ${response.status}`);
  return response.json();
}
