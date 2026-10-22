"""Check that the simulation's threshold rule and the overbooking service decide the same way.

The service (overbooking-service/overbooking_service/rules.py) is imported, not changed. Random
slots (risks of the booked patients, capacity, overbooks so far) are fed to both and the answers
compared. Also prints the setting differences between config.yaml and the simulation defaults.

    python simulation/parity_check.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SERVICE = HERE.parent / "overbooking-service"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SERVICE))

import clinic_sim as cs  # noqa: E402

from overbooking_service.rules import OverbookingRule, decide  # noqa: E402


def main() -> int:
    rng = np.random.default_rng(7)
    mismatches, total = [], 20000
    for _ in range(total):
        threshold = float(rng.choice([0.1, 0.2, 0.3, 0.4, 0.5]))
        limit = int(rng.integers(0, 9))
        capacity = int(rng.integers(1, 4))
        n = int(rng.integers(0, capacity + 1))
        risks = [float(x) for x in rng.beta(2, 4, n)]
        used = int(rng.integers(0, 9))
        service = decide(
            risks, capacity, used, OverbookingRule(threshold=threshold, daily_overbook_limit=limit)
        ).allow
        if not risks:
            sim = True  # the simulation books an empty slot without asking the policy
        else:
            sim = cs.threshold_rule(threshold, max_per_slot=capacity, daily_limit=limit)(
                risks, used
            )
        if service != sim:
            mismatches.append((risks, capacity, used, threshold, limit, service, sim))
    print(f"{total} random slots compared: {len(mismatches)} differences")
    for m in mismatches[:5]:
        print("  risks, capacity, used, threshold, limit, service, sim =", m)

    text = (SERVICE / "config.yaml").read_text(encoding="utf-8")

    def setting(key: str) -> str:
        return re.search(rf"^\s*{key}:\s*(\S+)", text, re.M).group(1)

    path = HERE.parent / "docs" / "decisions.json"
    decisions = json.loads(path.read_text(encoding="utf-8"))
    wanted = {
        "threshold": decisions["threshold"],
        "daily_overbook_limit": decisions["daily_limit"],
        "service_minutes": decisions["service_mean_min"],
    }
    print("\nSettings: service config.yaml vs docs/decisions.json")
    for key, value in wanted.items():
        have = float(setting(key))
        flag = "ok" if have == value else "DIFFERS: CEN must update config.yaml and its tests"
        print(f"  {key:22s} service {have:g}  decision {value:g}  {flag}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
