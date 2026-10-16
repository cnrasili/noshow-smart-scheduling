"""Create an administrator account of the admin service.

Usage: python -m admin_service.create_admin --email admin@hospital.local
The password is asked twice; --password-stdin reads it from standard input instead.
"""

import argparse
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from admin_service.security import MIN_PASSWORD_LENGTH, hash_password
from noshow_db import SessionLocal
from noshow_db.models.admin import AdminUser


def create_admin(session: Session, email: str, password: str) -> AdminUser:
    email = email.strip().lower()
    if "@" not in email:
        raise ValueError("Enter a valid email address")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"The password must have at least {MIN_PASSWORD_LENGTH} characters")
    if session.scalar(select(AdminUser.id).where(AdminUser.email == email)):
        raise ValueError(f"An administrator with {email} already exists")
    admin = AdminUser(email=email, password_hash=hash_password(password))
    session.add(admin)
    session.commit()
    return admin


def read_password(from_stdin: bool) -> str:
    if from_stdin:
        # Windows pipes and files end the line with \r\n
        return sys.stdin.readline().rstrip("\r\n")
    password = getpass.getpass("Password: ")
    if getpass.getpass("Repeat password: ") != password:
        raise ValueError("The passwords do not match")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    try:
        password = read_password(args.password_stdin)
        with SessionLocal() as session:
            email = create_admin(session, args.email, password).email
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(f"Administrator {email} created.")


if __name__ == "__main__":
    main()
