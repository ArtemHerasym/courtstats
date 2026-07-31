# CourtStats Data Model and Statistical Rules

## 1. MVP workflow

1. Create a season.
2. Create the season roster.
3. Create opponents as needed.
4. Create a game.
5. Enter statistics for all roster players.
6. Complete the game after validation.
7. Automatically calculate game and season statistics.

Accounts and authentication are excluded from the MVP.

---

## 2. Core entities

### Team

Represents JCP and opponent teams.

Fields:

* `id`
* `name` — required and case-insensitively unique
* `abbreviation` — optional
* `created_at`
* `updated_at`

Opponents are reusable Team records. When creating a game, the user can select an existing opponent or create a new one.

### Season

Fields:

* `id`
* `team_id`
* `name`
* `start_date` — optional
* `end_date` — optional
* `status` — `SETUP`, `ACTIVE`, or `COMPLETED`
* `created_at`
* `updated_at`

Rules:

* Season name is required.
* A team cannot have duplicate season names.
* End date cannot precede start date.
* Completed seasons remain viewable and can be reopened for corrections.

### Player

Fields:

* `id`
* `full_name`
* `display_name` — optional
* `created_at`
* `updated_at`

Rules:

* Full name is required.
* Player names are not unique because different players may share a name.
* When display name is empty, show full name.

### SeasonRoster

Fields:

* `id`
* `season_id`
* `player_id`
* `jersey_number` — optional
* `position` — optional
* `grade_level` — optional
* `status` — `ACTIVE`, `INACTIVE`, or `LEFT_TEAM`
* `created_at`
* `updated_at`

Rules:

* A player may appear only once in a season.
* Jersey number must be a nonnegative integer.
* Active players in one season cannot share a jersey number.
* New roster records begin as `ACTIVE`.

### Game

Fields:

* `id`
* `season_id`
* `opponent_team_id`
* `game_date`
* `venue_type` — `HOME`, `AWAY`, or `NEUTRAL`
* `opponent_score` — optional while draft
* `status` — `DRAFT` or `COMPLETED`
* `notes` — optional
* `created_at`
* `updated_at`

Rules:

* A game begins as `DRAFT`.
* Draft games are excluded from season statistics.
* Completed games remain editable.
* Changes to completed games trigger validation and recalculation.
* An opponent cannot be the season’s own team.
* Multiple games against the same opponent on the same date are allowed.

### PlayerGameStats

Fields:

* `id`
* `game_id`
* `season_roster_id`
* `participation_status` — `PLAYED` or `DID_NOT_PLAY`
* `three_point_attempts`
* `three_point_made`
* `two_point_attempts`
* `two_point_made`
* `free_throw_attempts`
* `free_throw_made`
* `turnovers`
* `assists`
* `offensive_rebounds`
* `defensive_rebounds`
* `steals`
* `deflections`
* `personal_fouls`
* `notes` — optional
* `created_at`
* `updated_at`

Rules:

* One statistics row per player per game.
* Statistical fields default to zero.
* `DID_NOT_PLAY` requires every statistic to be zero.
* `PLAYED` may contain all-zero statistics.
* A statistics row must reference a player from the game’s season roster.

---

## 3. Relationships

```text
Team
└── Season
    ├── SeasonRoster
    │   └── Player
    └── Game
        ├── Opponent Team
        └── PlayerGameStats
            └── SeasonRoster
```

---

## 4. Calculated statistics

These values are calculated and are not stored manually.

```text
Points = (2 × 2PM) + (3 × 3PM) + FTM

Total Rebounds = Offensive Rebounds + Defensive Rebounds

FGM = 2PM + 3PM

FGA = 2PA + 3PA

FG% = FGM ÷ FGA

2P% = 2PM ÷ 2PA

3P% = 3PM ÷ 3PA

FT% = FTM ÷ FTA

TS% = Points ÷ [2 × (FGA + 0.44 × FTA)]

A:TO = Assists ÷ Turnovers
```

### Undefined values

* A shooting percentage with zero attempts displays `—`.
* TS% displays `—` when both FGA and FTA are zero.
* A:TO with zero assists and zero turnovers displays `—`.
* A:TO with assists but zero turnovers displays the assists value.

### Season aggregation

Season shooting percentages use combined makes and attempts:

```text
Season FG% = Total FGM ÷ Total FGA
```

Do not average game percentages.

Season A:TO uses total assists divided by total turnovers.

### Team calculations

```text
Team Score = sum of player points

Score Margin = Team Score − Opponent Score
```

Results:

* Positive margin → `WIN`
* Negative margin → `LOSS`
* Zero margin → `TIE`

Only completed games count toward season summaries.

### Player season averages

Games played count only records marked `PLAYED`.

```text
Points Per Game = Total Points ÷ Games Played

Assists Per Game = Total Assists ÷ Games Played

Rebounds Per Game = Total Rebounds ÷ Games Played
```

When games played equals zero, display `—`.

### Team record

```text
Wins = completed WIN games

Losses = completed LOSS games

Win Percentage = Wins ÷ (Wins + Losses)
```

Ties are displayed separately and excluded from win percentage.

---

## 5. Validation rules

### Player statistics

* All statistics must be nonnegative integers.
* `2PM ≤ 2PA`
* `3PM ≤ 3PA`
* `FTM ≤ FTA`
* `DID_NOT_PLAY` requires all statistics to equal zero.
* The same player cannot appear twice in one game.
* The player must belong to the game’s season roster.
* Suspicious-value warnings are postponed until after the MVP.

### Completing a game

A game may remain incomplete as `DRAFT`.

To become `COMPLETED`, it requires:

* Valid game date
* Opponent
* Venue type
* Nonnegative integer opponent score
* One statistics row for every active roster player
* Participation status for every player
* All player-stat validations passing
* At least one player marked `PLAYED`

### Date entry

* Use a manual text field.
* Required format: `MM/DD/YYYY`
* Example: `10/29/2026`
* Do not provide a date picker.
* Incorrect separators and impossible dates produce validation errors.
* Past and future dates are allowed.
* Future games may be created as drafts.
* A future-dated game cannot be marked completed before its game date.
* Store the parsed value as a PostgreSQL `date`, not text.

---

## 6. Form input types

Use an input type appropriate for each value:

* Venue: dropdown with `HOME`, `AWAY`, and `NEUTRAL`
* Participation: selector with `PLAYED` and `DID_NOT_PLAY`
* Status fields: dropdowns
* Date: manual formatted text input
* Scores and statistics: nonnegative integer inputs
* Opponent: existing-team selector plus Add New Opponent
* Names and notes: text inputs

If any statistic is nonzero, participation must be `PLAYED`. `DID_NOT_PLAY` can be selected only when all statistics are zero.

---

## 7. Workbook import mapping

### Team Roster sheet

| Workbook column | Destination                  |
| --------------- | ---------------------------- |
| Player Name     | `Player.full_name`           |
| Jersey Number   | `SeasonRoster.jersey_number` |
| Position        | `SeasonRoster.position`      |
| Grade           | `SeasonRoster.grade_level`   |

Import defaults:

* `display_name` remains empty.
* Roster status becomes `ACTIVE`.
* Remove `#` from jersey numbers and store them as integers.

### Games

| Workbook value | Destination                  |
| -------------- | ---------------------------- |
| Game ID        | Temporary import identifier  |
| Date           | `Game.game_date`             |
| Opponent       | Find or create opponent Team |
| Home/Away      | `Game.venue_type`            |
| Opponent score | `Game.opponent_score`        |
| Season         | `Game.season_id`             |

Do not store imported team score or result. Recalculate them from raw data.

### Player statistics

| Workbook column | Destination                 |
| --------------- | --------------------------- |
| Player Name     | Match to `season_roster_id` |
| 3PTA            | `three_point_attempts`      |
| 3PTM            | `three_point_made`          |
| 2PTA            | `two_point_attempts`        |
| 2PTM            | `two_point_made`            |
| FTA             | `free_throw_attempts`       |
| FTM             | `free_throw_made`           |
| TO              | `turnovers`                 |
| Assists         | `assists`                   |
| Off. Reb.       | `offensive_rebounds`        |
| Def. Reb.       | `defensive_rebounds`        |
| Steals          | `steals`                    |
| Defl.           | `deflections`               |
| Pers. Fouls     | `personal_fouls`            |

Skip:

* Team Total rows
* Empty spreadsheet columns
* Stored points
* Stored rebounds
* FGM and FGA
* Percentages
* Team score
* Result
* Averages

Workbook calculations are used only to verify CourtStats results. Known legacy values such as `Avay` are normalized to `AWAY`.

---

## 8. Required statistical tests

* Points calculation
* Rebound calculation
* FGM and FGA calculation
* Shooting percentages
* Zero-attempt behavior
* Combined season percentages
* True shooting percentage
* Assist-to-turnover ratio
* Team score
* Game result and margin
* Player per-game averages
* `DID_NOT_PLAY` exclusion
* Draft-game exclusion

## 9. Required validation tests

* Negative statistics rejected
* Decimal statistics rejected
* Makes exceeding attempts rejected
* `DID_NOT_PLAY` with nonzero statistics rejected
* `PLAYED` with all-zero statistics accepted
* Duplicate player-game row rejected
* Wrong-season player rejected
* Missing opponent score prevents completion
* Negative opponent score rejected
* Completion with no participating players rejected
* Incomplete draft accepted
* Future draft accepted
* Future completed game rejected
* Wrong date format rejected
* Impossible date rejected
* Duplicate roster player rejected
* Duplicate active jersey number rejected
