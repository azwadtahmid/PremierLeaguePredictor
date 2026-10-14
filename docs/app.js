// Premier League Predictor: renders docs/data.json (built by src/site.py).

const UK = "Europe/London";
const pct = (v, digits = 0) => (v == null ? "–" : `${(v * 100).toFixed(digits)}%`);
// Chances never round to certainty: 0.9982 shows as ">99%", 0.0004 as "<0.1%".
const chance = (v) => {
  if (v == null) return "–";
  if (v === 0 || v === 1) return pct(v);
  if (v < 0.001) return "<0.1%";
  if (v < 0.01) return pct(v, 1);
  if (v > 0.995) return ">99%";
  return pct(v);
};
const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) if (child != null) node.append(child);
  return node;
};
const fmt = (iso, options) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: UK, ...options }).format(new Date(iso));

const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const SERIES_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];
const isDark = () => matchMedia("(prefers-color-scheme: dark)").matches
  && document.documentElement.dataset.theme !== "light";

let DATA;
let current;

fetch("data.json", { cache: "no-cache" })
  .then((r) => r.json())
  .then((data) => {
    DATA = data;
    renderHeader();
    renderRecord();
    setupMatchweeks();
    renderPredictedTable();
    renderRaces();
    renderRealTable();
    renderTestTable();
  })
  .catch(() => {
    document.getElementById("updated").textContent = "Couldn't load the data. Try refreshing.";
  });

function renderHeader() {
  document.getElementById("season").textContent = DATA.season;
  document.getElementById("updated").textContent =
    `Updated ${fmt(DATA.updated, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} UK time`;
}

function card(label, value, sub) {
  return el("div", { class: "card" },
    el("div", { class: "label", text: label }),
    el("div", { class: "value", text: value }),
    sub ? el("div", { class: "sub", text: sub }) : null);
}

function renderRecord() {
  const { locked, backtest } = DATA.track_record;
  const record = locked || backtest;
  const note = document.getElementById("record-note");
  const box = document.getElementById("record");
  if (!record) { note.textContent = "No matches scored yet."; return; }

  if (locked) {
    note.textContent = `Live predictions, locked before kick-off: ${locked.matches} matches scored.` +
      (backtest ? ` (Backtest for the ${backtest.matches} matches before tracking began: ${pct(backtest.accuracy)} right.)` : "");
  } else {
    note.textContent = `No live predictions have been played yet: the first are locked before the next matchweek. ` +
      `Until then, this is a backtest of the ${backtest.matches} matches already played, using only results from before each match.`;
  }
  box.append(
    card("Results right", pct(record.accuracy, 1), `${record.results_right} of ${record.matches}`),
    card("Exact scores", String(record.exact_scores), `${pct(record.exact_scores / record.matches, 1)} of matches`),
    card("Points", String(record.points), "3 exact score · 1 right result"),
    card("Bet365 favourite", pct(record.bookmaker_accuracy, 1), "results right"),
    card("Always home win", pct(record.home_win_accuracy, 1), "results right"),
  );
}

// ---------- Matchweeks ----------

function setupMatchweeks() {
  const select = document.getElementById("mw-select");
  for (const round of DATA.rounds) {
    const label = { complete: "played", "in progress": "in progress", upcoming: "upcoming" }[round.state];
    select.append(el("option", { value: round.round, text: `Matchweek ${round.round} · ${label}` }));
  }
  const fromHash = Number(new URLSearchParams(location.hash.slice(1)).get("mw"));
  const start = DATA.rounds.some((r) => r.round === fromHash) ? fromHash
    : (DATA.next_round ?? DATA.latest_completed_round ?? 1);
  select.addEventListener("change", () => showRound(Number(select.value)));
  document.getElementById("mw-prev").addEventListener("click", () => showRound(current - 1));
  document.getElementById("mw-next").addEventListener("click", () => showRound(current + 1));
  showRound(start);
}

function showRound(number) {
  const round = DATA.rounds.find((r) => r.round === number);
  if (!round) return;
  current = number;
  history.replaceState(null, "", `#mw=${number}`);
  document.getElementById("mw-select").value = number;
  document.getElementById("mw-prev").disabled = number === DATA.rounds[0].round;
  document.getElementById("mw-next").disabled = number === DATA.rounds[DATA.rounds.length - 1].round;
  document.getElementById("mw-title").textContent = `Matchweek ${number}`;

  const first = round.fixtures[0].kickoff;
  const last = round.fixtures[round.fixtures.length - 1].kickoff;
  const range = fmt(first, { day: "numeric", month: "short" }) === fmt(last, { day: "numeric", month: "short" })
    ? fmt(first, { weekday: "short", day: "numeric", month: "short" })
    : `${fmt(first, { day: "numeric", month: "short" })} – ${fmt(last, { day: "numeric", month: "short" })}`;
  const state = { complete: "Played", "in progress": "In progress", upcoming: "Upcoming" }[round.state];
  document.getElementById("mw-note").textContent = `${state} · ${range} · kick-off times are UK time`;

  const summary = document.getElementById("mw-summary");
  summary.replaceChildren();
  const s = round.summary;
  if (s) {
    const chip = (label, value) => el("span", { class: "chip" }, el("strong", { text: value }), ` ${label}`);
    summary.append(
      chip("results right", `${s.results_right}/${s.matches}`),
      chip("exact scores", String(s.exact_scores)),
      chip("points", String(s.points)),
      s.bookmaker_accuracy != null ? chip("for the Bet365 favourite", `${Math.round(s.bookmaker_accuracy * s.matches)}/${s.matches}`) : null,
      chip("for always home", `${Math.round(s.home_win_accuracy * s.matches)}/${s.matches}`),
    );
  }

  const list = document.getElementById("fixtures");
  list.replaceChildren();
  const days = new Map();
  for (const f of round.fixtures) {
    const day = fmt(f.kickoff, { weekday: "long", day: "numeric", month: "long" });
    if (!days.has(day)) days.set(day, []);
    days.get(day).push(f);
  }
  for (const [day, fixtures] of days) {
    const block = el("div", { class: "day" }, el("h3", { text: day }));
    fixtures.forEach((f) => block.append(fixtureRow(f)));
    list.append(block);
  }
}

function fixtureRow(f) {
  const p = f.prediction;
  const time = f.status === "postponed" ? "P–P" : fmt(f.kickoff, { hour: "2-digit", minute: "2-digit" });

  const tagClass = { locked: "tag-locked", provisional: "tag-provisional", backtest: "tag-backtest" }[p.source];
  const tagText = { locked: "Locked", provisional: "Provisional", backtest: "Backtest" }[p.source];
  const pred = el("div", { class: "score-box pred" },
    el("span", { class: "label" }, el("span", { class: `tag ${tagClass}`, text: tagText })),
    el("span", { class: "score", text: p.score.replace("-", " – ") }));

  let result;
  if (f.status === "played") {
    const good = f.correct_result;
    const verdict = f.correct_score ? "✓ Exact +3" : good ? "✓ Result +1" : "✗ Wrong 0";
    result = el("div", { class: `result-box ${good ? "good" : "bad"}` },
      el("span", { class: "score", text: f.score.replace("-", " – ") }),
      el("span", { class: "verdict", text: verdict }));
  } else {
    result = el("div", { class: "result-box pending" },
      el("span", { class: "label", text: f.status === "postponed" ? "Postponed" : "Result" }),
      el("span", { class: "score", text: "–" }));
  }

  const { H, D, A } = p.probs;
  const bar = el("div", { class: "bar", role: "img",
    "aria-label": `Home win ${pct(H)}, draw ${pct(D)}, away win ${pct(A)}` },
  el("span", { class: "h", style: `width:${H * 100}%` }),
  el("span", { class: "d", style: `width:${D * 100}%` }),
  el("span", { class: "a", style: `width:${A * 100}%` }));
  const nums = el("div", { class: "nums" },
    el("span", {}, el("span", { class: "dot", style: "background:var(--home)" }), `Home ${pct(H)}`),
    el("span", {}, el("span", { class: "dot", style: "background:var(--draw)" }), `Draw ${pct(D)}`),
    el("span", {}, el("span", { class: "dot", style: "background:var(--away)" }), `Away ${pct(A)}`));
  const probs = el("div", { class: "probs" }, nums, bar,
    el("div", { class: "likely", text: `Likely: ${p.likely}` }));

  const row = el("div", { class: "fixture" },
    el("div", { class: "time", text: time }),
    el("div", { class: "team home", text: f.home, title: f.home }),
    pred,
    el("div", { class: "team away", text: f.away, title: f.away }),
    result,
    probs);
  const lockedAt = p.locked_at ? ` Locked ${fmt(p.locked_at, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.` : "";
  attachTooltip(row, () =>
    `Expected goals ${p.xg[0].toFixed(2)} – ${p.xg[1].toFixed(2)}.${lockedAt}` +
    (f.bookmaker_pick ? ` Bet365 favourite: ${{ H: "home win", D: "draw", A: "away win" }[f.bookmaker_pick]}.` : ""));
  return row;
}

// ---------- Tables ----------

function changeText(value, { digits = 0, percent = false, invert = false } = {}) {
  if (value == null) return null;
  const shown = percent ? value * 100 : value;
  if (Math.abs(shown) < (percent ? 0.5 : 0.05)) return el("span", { class: "change", text: "no change" });
  const better = invert ? value < 0 : value > 0;
  const sign = shown > 0 ? "+" : "−";
  const text = `${shown > 0 ? "▲" : "▼"} ${sign}${Math.abs(shown).toFixed(digits)}${percent ? " pts" : ""}`;
  return el("span", { class: `change ${better ? "up" : "down"}`, text });
}

function renderPredictedTable() {
  const pt = DATA.predicted_table;
  const table = document.getElementById("pred-table");
  const note = document.getElementById("pred-note");
  if (!pt) { note.textContent = "Appears after the first completed matchweek."; return; }
  note.textContent = pt.compared_with
    ? `After matchweek ${pt.after_round}. Changes are since matchweek ${pt.compared_with}; percentage changes are in percentage points.`
    : `After matchweek ${pt.after_round}.`;

  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Pos" }), el("th", { class: "left", text: "Move" }), el("th", { class: "left", text: "Team" }),
    el("th", { text: "Pts now" }), el("th", { text: "Expected pts" }),
    el("th", { text: "Champion" }), el("th", { text: "Top 4" }), el("th", { text: "Relegated" }))));
  const body = el("tbody");
  for (const r of pt.rows) {
    const c = r.change || {};
    const move = c.position == null ? "–" : c.position === 0 ? "–" : c.position > 0 ? `▲ ${c.position}` : `▼ ${-c.position}`;
    const moveClass = c.position > 0 ? "up" : c.position < 0 ? "down" : "";
    const zone = r.position <= 4 ? "zone-top" : r.position > pt.rows.length - 3 ? "zone-bottom" : "";
    const cut = r.position === 4 || r.position === pt.rows.length - 3 ? " cut-top" : "";
    const probCell = (v, change, invert) => {
      const td = el("td", { class: "prob-cell" }, el("span", { class: "v", text: chance(v) }),
        changeText(change, { percent: true, invert }));
      td.style.background = `rgba(var(--heat), ${Math.min(v, 1) * 0.28})`;
      return td;
    };
    body.append(el("tr", { class: zone + cut },
      el("td", { text: String(r.position) }),
      el("td", { class: `left pos-change ${moveClass}`, text: move }),
      el("td", { class: "left team", text: r.team }),
      el("td", { text: String(r.points_now) }),
      el("td", {}, el("span", { text: r.expected_points.toFixed(0) }), changeText(c.expected_points, { digits: 1 })),
      probCell(r.champion, c.champion, false),
      probCell(r.top_4, c.top_4, false),
      probCell(r.relegated, c.relegated, true)));
  }
  table.append(body);
  table.parentElement.after(el("div", { class: "zones" },
    el("span", { class: "top", text: "Top 4 (Champions League)" }), el("span", { class: "bottom", text: "Relegation" })));
}

function renderRealTable() {
  const table = document.getElementById("real-table");
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Pos" }), el("th", { class: "left", text: "Team" }),
    ...["P", "W", "D", "L", "GF", "GA", "GD", "Pts"].map((h) => el("th", { text: h })))));
  const body = el("tbody");
  DATA.table.forEach((r, i) => {
    const zone = i < 4 ? "zone-top" : i >= DATA.table.length - 3 ? "zone-bottom" : "";
    body.append(el("tr", { class: zone },
      el("td", { text: String(i + 1) }), el("td", { class: "left team", text: r.team }),
      ...[r.played, r.won, r.drawn, r.lost, r.gf, r.ga, (r.gd > 0 ? "+" : "") + r.gd, r.points]
        .map((v, j) => el("td", j === 7 ? { text: String(v), style: "font-weight:700" } : { text: String(v) }))));
  });
  table.append(body);
}

function renderTestTable() {
  const rows = DATA.test_metrics;
  if (!rows) return;
  const table = document.getElementById("test-table");
  table.append(el("thead", {}, el("tr", {},
    el("th", { class: "left", text: "2025/26 test season" }), el("th", { text: "Results right" }),
    el("th", { text: "Log loss (lower is better)" }), el("th", { text: "Exact scores" }))));
  const body = el("tbody");
  for (const r of rows) {
    body.append(el("tr", {},
      el("td", { class: "left", text: r.model }), el("td", { text: pct(r.accuracy, 1) }),
      el("td", { text: r.log_loss.toFixed(3) }), el("td", { text: r.exact_score == null ? "–" : pct(r.exact_score, 1) })));
  }
  table.append(body);
}

// ---------- Race charts ----------

function renderRaces() {
  lineChart("title-race", "Title race: chance of winning the league", DATA.title_race);
  lineChart("relegation-race", "Relegation battle: chance of going down", DATA.relegation_race);
}

function lineChart(id, caption, race) {
  const fig = document.getElementById(id);
  fig.append(el("figcaption", { text: caption }));
  if (!race || race.rounds.length < 2) {
    fig.append(el("p", { class: "small", text: "Appears after two completed matchweeks." }));
    return;
  }
  const W = 460, H = 220, M = { l: 34, r: 92, t: 8, b: 26 };
  const x = (i) => M.l + (i / (race.rounds.length - 1)) * (W - M.l - M.r);
  const y = (v) => M.t + (1 - v) * (H - M.t - M.b);
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${caption}: ` + race.teams.map((t) => `${t.team} ${pct(t.values.at(-1))}`).join(", "));
  const add = (parent, tag, attrs) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    parent.append(n);
    return n;
  };

  const grid = add(svg, "g", { class: "grid" });
  const axis = add(svg, "g", { class: "axis" });
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    add(grid, "line", { x1: M.l, x2: W - M.r, y1: y(v), y2: y(v) });
    add(axis, "text", { x: M.l - 6, y: y(v) + 4, "text-anchor": "end" }).textContent = `${v * 100}%`;
  }
  race.rounds.forEach((r, i) => {
    add(axis, "text", { x: x(i), y: H - 8, "text-anchor": "middle" }).textContent = `MW${r}`;
  });

  const palette = isDark() ? SERIES_DARK : SERIES;
  const teams = race.teams.slice(0, 8);
  const legend = el("div", { class: "chart-legend" });
  const labelYs = [];
  teams.forEach((t, k) => {
    const colour = palette[k];
    const points = t.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
    add(svg, "polyline", { class: "series-line", points, stroke: colour });
    t.values.forEach((v, i) => {
      add(svg, "circle", { cx: x(i), cy: y(v), r: 3, fill: colour });
      const hit = add(svg, "circle", { class: "hit", cx: x(i), cy: y(v), r: 10 });
      attachTooltip(hit, () => `${t.team}, after matchweek ${race.rounds[i]}: ${chance(v)}`);
    });
    if (k < 4) {  // direct labels for the first four, nudged apart if they collide
      let ly = y(t.values.at(-1)) + 4;
      for (const other of labelYs) if (Math.abs(other - ly) < 12) ly = other + 12;
      labelYs.push(ly);
      add(svg, "text", { class: "label", x: x(race.rounds.length - 1) + 8, y: ly })
        .textContent = `${t.team} ${chance(t.values.at(-1))}`;
    }
    legend.append(el("span", {}, el("span", { class: "swatch", style: `background:${colour}` }), t.team));
  });
  fig.append(svg, legend);
}

// ---------- Tooltip ----------

function attachTooltip(target, text) {
  const tip = document.getElementById("tooltip");
  const show = (event) => {
    tip.textContent = text();
    tip.hidden = false;
    const x = Math.min(event.clientX + 12, innerWidth - tip.offsetWidth - 8);
    tip.style.left = `${x}px`;
    tip.style.top = `${event.clientY + 14}px`;
  };
  target.addEventListener("mousemove", show);
  target.addEventListener("mouseleave", () => { tip.hidden = true; });
}
