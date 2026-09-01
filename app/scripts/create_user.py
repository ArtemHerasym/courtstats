from getpass import getpass

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User
from app.services.auth import get_user_by_username


def main() -> int:
    username = input("Username: ").strip()

    if not username:
        print("Username cannot be blank.")
        return 1

    password = getpass("Password: ")

    if not password:
        print("Password cannot be blank.")
        return 1

    password_confirmation = getpass(
        "Confirm password: "
    )

    if password != password_confirmation:
        print("Passwords do not match.")
        return 1

    with SessionLocal() as db:
        existing_user = get_user_by_username(
            db,
            username,
        )

        if existing_user is not None:
            print(
                "A user with this username "
                "already exists."
            )
            return 1

        user = User(
            username=username,
            password_hash=hash_password(password),
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)

        except IntegrityError:
            db.rollback()

            print(
                "A user with this username "
                "already exists."
            )
            return 1

    print(
        f"User '{user.username}' "
        "created successfully."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())