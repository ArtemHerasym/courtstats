from getpass import getpass

from app.database.session import (
    SessionLocal,
)
from app.services.auth import (
    UserAlreadyExistsError,
    create_user,
)


def main() -> None:
    print(
        "CourtStats User Setup"
    )
    print(
        "---------------------"
    )

    username = input(
        "Username: "
    ).strip()

    password = getpass(
        "Password: "
    )

    password_confirmation = getpass(
        "Confirm password: "
    )

    if password != password_confirmation:
        print(
            "Error: passwords do not match."
        )
        return

    try:
        with SessionLocal() as db:
            user = create_user(
                db,
                username,
                password,
            )

    except (
        ValueError,
        UserAlreadyExistsError,
    ) as exc:
        print(
            f"Error: {exc}"
        )
        return

    except Exception as exc:
        print(
            "Error: user could not be created."
        )
        print(
            f"Details: {exc}"
        )
        return

    print()
    print(
        "CourtStats user created successfully."
    )
    print(
        f"Username: {user.username}"
    )


if __name__ == "__main__":
    main()