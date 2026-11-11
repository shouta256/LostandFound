"""Assign local development roles to users who have already signed in."""

import argparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User


ROLES = ("student", "team_member")


def set_role(db: Session, email: str, role: str) -> int:
    if role not in ROLES:
        raise ValueError("Role must be student or team_member.")
    users = db.scalars(select(User).where(func.lower(User.email) == email.lower())).all()
    for user in users:
        user.role = role
    db.flush()
    return len(users)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("role", choices=ROLES)
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        updated = set_role(db, args.email, args.role)
        if not updated:
            parser.exit(1, f"No user matches {args.email}. The user must sign in once first.\n")
        emails = db.scalars(select(User.email).where(func.lower(User.email) == args.email.lower())).all()
    for email in emails:
        print(f"{email}: {args.role}")


if __name__ == "__main__":
    main()
