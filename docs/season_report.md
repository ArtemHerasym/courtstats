# Public 2025–26 season case study

`GET /season-report/2025-26` is a static Jinja page backed by the checked-in
`app/data/season_report_2025_26.json` snapshot. Its router has no database,
authentication, or CSRF dependencies and implements no write methods. Existing
protected routers and their dependencies are unchanged. The report overrides the
base template's account-action block so no logout form or session value appears.
The homepage contains the single discovery link; application links still require
sign-in.

## Publishing verified analysis

The snapshot and the remaining empty collections at the top of
`app/templates/season_report.html` are the publication boundary. Fill them only
after verifying the raw records. Do not
connect this public page to operational models, live rosters, or private notes.
Player labels must be approved jersey numbers, initials, or display labels.

Populated: explicit season-summary metrics, chronological game scores, player
production and shooting summaries, and the four team findings subsequently
supplied by the user: ball security, rebounding, shooting conversion, and season
progression. The executive summary and major findings preserve those conclusions
with sample sizes and cautious wording. Practical implications are limited to
game review and future evidence collection based on those findings.

Pending: player consistency/distribution analysis and further player-specific
interpretive findings. Jinja comments identify the pending locations and are
removed from public HTML.

## Source verification, September 13, 2026

Source workbook: **JCP 2025–26 Season Analytics Evidence**, supplied by the user.
Read through the Google Drive connector; the workbook was not modified. The
production page makes no Google requests. Raw student names and grades were
excluded from the checked-in snapshot and all public content. The source link
is intentionally not published on the report because the workbook contains
student names and grades.

Ranges inspected: `README!A1:J60`, `Games!A1:G16`,
`'Player Stats'!A1:T121`, `'Season Summary'!A4:N30` (values and formulas),
and the roster's jersey mapping. Every team and player summary value reconciled
with independently recomputed raw aggregates. All 120 observations were unique;
all point formulas, makes-versus-attempts checks, game score reconciliations,
and game-result checks passed. Team points total 998; opponent points total
1,065. Combined field goals are 406 / 833.

The user subsequently supplied verified win/loss and first/final-five-game
comparisons. These were checked against the raw records and included with the
user's exact published values, including 7.3 offensive rebounds per game in
losses and the +16.9 rebound difference. Do not recompute rounded published
values using a different rounding convention. No middle-group metrics were
invented; only its supplied 3–2 record is published. No consistency statistics,
correlations, statistical significance, or causal effects were generated.

The workbook's player GP formula counts matching rows. The report labels it
**observations**, and explains that PPG/RPG use those counts rather than verified
appearances. The original absence of explicit DNP status remains visible.

`components/season_report.html` provides chart and finding macros. The chart
contract is documented above the macro. Supply finding-led titles, units, sample
sizes, interpretation, caution, and an exact-value HTML table matching the
datasets. Use `progression` for chronological lines, `player` for horizontal
bars, and `comparison` for grouped bars. Prefer distribution tables or dot plots
for consistency; add a specialized visual only when verified evidence warrants
it. Do not connect unordered observations with lines or force scatter plots.

Aggregate shooting makes and attempts before dividing. Do not average game
percentages. Undefined values remain `null` in charts and clearly labeled in
table cells. Resolve original PLAYED/DNP ambiguity before setting per-game
denominators. Include attempts and observations beside player comparisons.

Charts use the existing pinned Chart.js version and `dashboard.js` helpers.
`app.js` owns theme persistence; the adapter listens to its existing event.
Reduced-motion changes rebuild without animation. On missing or failed chart
rendering, the visible exact-value table remains available. The current edition
contains a season scoring comparison, four win/loss comparison charts,
two first/final-five comparison charts, chronological scoring lines, and a
horizontal chart of player scoring totals using public jersey labels. Turnover
counts and AST:TOV ratios use separate scales; shooting percentage comparisons
use a zero-to-100 scale. Each chart has an exact-value HTML alternative.

## Verification

Run the existing PostgreSQL test setup, then:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
node tests/test_season_report_charts.cjs
```

Review `/season-report/2025-26` at desktop, tablet, and mobile widths in both
themes. Check menu Escape/focus behavior, anchors, expanded dictionary overflow,
theme persistence after reload, and readable fallback tables when charts are
eventually populated. The public route must continue to work without database
access and must never unlock existing private pages or APIs.

### Completed checks

- Full Python suite: 732 passed (only existing SlowAPI deprecation warnings).
- Report tests after final markup adjustments: 28 passed.
- Chart adapter tests: 4 passed, including shared theme recoloring, reduced
  motion, percentage scales, and failed-library/data fallbacks.
- Visual review: desktop (1440px), tablet (768px), and mobile (390px), light
  and dark themes. All nine charts rendered without console warnings/errors.
- Page and canvas overflow checks: none at 320, 390, 768, 1024, or 1440px.
  Wide tables scroll within their labeled, keyboard-focusable containers.
- Shared theme persistence, menu Escape/focus handling, anchor navigation,
  and expandable dictionary checked in the browser.
