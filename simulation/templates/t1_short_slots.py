"""Template 1: shorter slots, no overbooking.

Idea: if the 15-minute slot is longer than the typical 12-minute consultation, the idle time is
built into the template. Shorten the slot to 12 minutes and book 20 patients without any
overbooking.
"""

from template_base import Template, render_html

TEMPLATE = Template(
    key="t1_short_slots",
    name="Template 1 - Short slots (12 min), no overbooking",
    idea=(
        "Fit more patients by matching the slot length to the consultation length "
        "instead of overbooking."
    ),
    n_slots=20,
    slot_min=12,
)

if __name__ == "__main__":
    print("Saved:", render_html(TEMPLATE))
