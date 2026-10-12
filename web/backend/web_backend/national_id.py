# Turkish national ID numbers (T.C. kimlik numarası): validation and fictional demo numbers

# Demo numbers start with this prefix so they are recognizable as made up
FICTIONAL_PREFIX = "99999"


def _check_digits(first_nine: str) -> str:
    digits = [int(c) for c in first_nine]
    tenth = (sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10
    eleventh = (sum(digits) + tenth) % 10
    return f"{tenth}{eleventh}"


def is_valid_national_id(value: str) -> bool:
    """11 digits, first digit not 0, and both official check digits correct."""
    if len(value) != 11 or not value.isascii() or not value.isdigit() or value[0] == "0":
        return False
    return value[9:] == _check_digits(value[:9])


def fictional_national_id(number: int) -> str:
    """A valid number with the fictional prefix; number is 0-9999 and makes it unique.

    These numbers are fictional and only used for demo and test data.
    """
    if not 0 <= number <= 9999:
        raise ValueError("number must be between 0 and 9999")
    first_nine = f"{FICTIONAL_PREFIX}{number:04d}"
    return first_nine + _check_digits(first_nine)
