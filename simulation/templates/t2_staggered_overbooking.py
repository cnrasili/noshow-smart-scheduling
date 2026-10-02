"""Template 2: 15-minute slots, risk-based overbooking, second patient staggered by half a slot.

Idea: a second patient booked at the same minute waits a whole consultation if both attend. Starting the
second patient half a slot later halves the collision.
"""
from template_base import Template, render_html

TEMPLATE = Template(
    key="t2_staggered_overbooking",
    name="Template 2 - Staggered overbooking (second patient +7.5 min)",
    idea="Same 15-minute slots as today, but the overbooked patient starts in the middle of the slot.",
    n_slots=16,
    slot_min=15,
    threshold=0.30,
    offset=0.5,
    thresholds_to_try=(0.20, 0.25, 0.30, 0.40),
)

if __name__ == "__main__":
    print("Saved:", render_html(TEMPLATE))
