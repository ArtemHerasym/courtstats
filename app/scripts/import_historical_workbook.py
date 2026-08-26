import sys
from pathlib import Path

from app.database.session import SessionLocal
from app.importers.historical_database import (
    HistoricalImportAlreadyExistsError,
    import_historical_data,
)
from app.importers.historical_workbook import (
    load_and_validate_historical_workbook,
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: poetry run python "
            "scripts/import_historical_workbook.py "
            "<workbook.xlsx>"
        )
        return 1

    workbook_path = Path(sys.argv[1])

    if not workbook_path.exists():
        print(
            f"Workbook not found: {workbook_path}"
        )
        return 1

    try:
        data = load_and_validate_historical_workbook(
            workbook_path
        )

        print(
            "Preflight passed: "
            f"{len(data.roster)} roster players, "
            f"{len(data.games)} games, "
            f"{len(data.player_stats)} player stat rows."
        )

        with SessionLocal() as db:
            season = import_historical_data(
                db,
                data,
            )

        print(
            f"Historical season {season.name} "
            "imported successfully."
        )

        return 0

    except HistoricalImportAlreadyExistsError as exc:
        print(f"Import aborted: {exc}")
        return 1

    except ValueError as exc:
        print(f"Historical workbook validation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())