import pytest

from overbooking_service.rules import OverbookingRule, decide

RULE = OverbookingRule(threshold=0.30, daily_overbook_limit=2)


@pytest.mark.parametrize(
    ("booked_risks", "daily_overbooks", "allow", "overbook", "reason"),
    [
        ([], 0, True, False, "Slot is empty"),
        ([], 5, True, False, "Slot is empty"),
        (
            [0.41],
            1,
            True,
            True,
            "Slot is booked; booked patient risk 0.41 >= 0.30; daily overbooks 1/2",
        ),
        (
            [0.30],
            0,
            True,
            True,
            "Slot is booked; booked patient risk 0.30 >= 0.30; daily overbooks 0/2",
        ),
        ([0.29], 0, False, False, "Slot is booked; booked patient risk 0.29 < 0.30"),
        (
            [0.80],
            2,
            False,
            False,
            "Slot is booked; booked patient risk 0.80 >= 0.30; daily overbook limit reached (2/2)",
        ),
        ([0.80, 0.90], 0, False, False, "Slot is full (2/2 patients)"),
    ],
)
def test_decide(booked_risks, daily_overbooks, allow, overbook, reason):
    decision = decide(booked_risks, 2, daily_overbooks, RULE)
    assert (decision.allow, decision.overbook, decision.reason) == (allow, overbook, reason)


def test_lowest_booked_risk_is_used():
    decision = decide([0.80, 0.10], 3, 0, RULE)
    assert not decision.allow
    assert "0.10 < 0.30" in decision.reason


def test_zero_daily_limit_disables_overbooking():
    rule = RULE.model_copy(update={"daily_overbook_limit": 0})
    assert not decide([0.90], 2, 0, rule).allow


@pytest.mark.parametrize(
    "values",
    [
        {"threshold": 1.5},
        {"daily_overbook_limit": -1},
    ],
)
def test_invalid_rule_is_rejected(values):
    with pytest.raises(ValueError):
        OverbookingRule(**{**RULE.model_dump(), **values})
