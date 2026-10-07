import pytest
from sqlalchemy.exc import IntegrityError

from web_backend.national_id import FICTIONAL_PREFIX, fictional_national_id, is_valid_national_id


@pytest.mark.parametrize("value", ["10000000146", "99999000184"])
def test_valid_numbers(value: str) -> None:
    assert is_valid_national_id(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1000000014",  # ten digits
        "100000001460",  # twelve digits
        "00000000146",  # first digit 0
        "10000000156",  # wrong tenth digit
        "10000000147",  # wrong eleventh digit
        "1000000014a",
        "１0000000146",  # full-width digit
    ],
)
def test_invalid_numbers(value: str) -> None:
    assert not is_valid_national_id(value)


def test_fictional_numbers_are_valid_unique_and_recognizable() -> None:
    numbers = [fictional_national_id(n) for n in range(10000)]

    assert all(is_valid_national_id(n) for n in numbers)
    assert all(n.startswith(FICTIONAL_PREFIX) for n in numbers)
    assert len(set(numbers)) == len(numbers)


@pytest.mark.parametrize("number", [-1, 10000])
def test_fictional_number_range(number: int) -> None:
    with pytest.raises(ValueError):
        fictional_national_id(number)


def test_database_rejects_a_duplicate_national_id(db, make_patient) -> None:
    make_patient(email="first@example.com", national_id="10000000146")

    with pytest.raises(IntegrityError):
        make_patient(email="second@example.com", national_id="10000000146")
