# CourtStats

CourtStats is a basketball statistics and analytics application being developed for the Jordan Christian Preparatory basketball program.

The project will replace the existing season statistics spreadsheet with a database-backed web application. The current version contains the backend and database foundation.

## Current Progress

- FastAPI application foundation
- PostgreSQL 17 through Docker Compose
- SQLAlchemy 2.x models
- Alembic database migrations
- Six core basketball entities
- Database integrity and constraint testing
- 28 passing automated tests

## Technology Stack

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- Pytest
- Docker Compose
- Poetry

## Data Model

The current database contains:

- Team
- Season
- Player
- SeasonRoster
- Game
- PlayerGameStats

Raw player-game statistics are stored in the database. Calculated values such as points, rebounds, percentages, team score, and season averages will be calculated from raw data rather than manually stored.

## Local Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd courtstats