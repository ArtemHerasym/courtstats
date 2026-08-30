from pathlib import Path

from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


def format_percentage(
    value: float | None,
) -> str:
    if value is None:
        return "—"

    return f"{value:.1%}"


templates.env.filters[
    "percentage"
] = format_percentage