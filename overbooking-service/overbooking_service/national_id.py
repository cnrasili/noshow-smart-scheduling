# Fictional Turkish national ID numbers for demo and test patients

# Same pattern as the web backend's demo numbers: prefix, four-digit number, check digits
FICTIONAL_PREFIX = "99999"


def fictional_national_id(number: int) -> str:
    """A valid national ID number with the fictional prefix; number is 0-9999.

    These numbers are fictional and only used for demo and test data.
    """
    if not 0 <= number <= 9999:
        raise ValueError("number must be between 0 and 9999")
    first_nine = f"{FICTIONAL_PREFIX}{number:04d}"
    digits = [int(c) for c in first_nine]
    tenth = (sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10
    eleventh = (sum(digits) + tenth) % 10
    return f"{first_nine}{tenth}{eleventh}"
