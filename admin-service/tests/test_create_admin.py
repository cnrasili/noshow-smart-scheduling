import io

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from admin_service.create_admin import create_admin, main
from admin_service.security import verify_password
from noshow_db.models.admin import AdminUser


def test_create_admin_stores_only_a_hash(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        create_admin(session, " Second@Hospital.local ", "another long password")
        admin = session.scalar(select(AdminUser).where(AdminUser.email == "second@hospital.local"))
    assert admin.password_hash.startswith("scrypt$")
    assert verify_password("another long password", admin.password_hash)


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("admin@hospital.local", "another long password", "already exists"),
        ("new@hospital.local", "short", "at least 12 characters"),
        ("not-an-email", "another long password", "valid email"),
    ],
)
def test_create_admin_rejects_invalid_input(
    session_factory: sessionmaker[Session], email: str, password: str, message: str
):
    with session_factory() as session, pytest.raises(ValueError, match=message):
        create_admin(session, email, password)


def test_command_creates_an_admin(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, capsys
):
    monkeypatch.setattr("admin_service.create_admin.SessionLocal", session_factory)
    monkeypatch.setattr(
        "sys.argv", ["create_admin", "--email", "cli@hospital.local", "--password-stdin"]
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("command line password\n"))
    main()
    assert capsys.readouterr().out == "Administrator cli@hospital.local created.\n"
