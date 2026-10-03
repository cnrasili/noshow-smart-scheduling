"""Template 3: a buffer slot in the middle, overbooking only after it and not in the last slot.

Idea: delays caused by overbooking spread to all later patients. A buffer slot lets the physician
catch up, and keeping overbooking away from the first half and the last slot limits cascades and
overtime.
"""

from template_base import Template, render_html

TEMPLATE = Template(
    key="t3_buffer_late_overbooking",
    name="Template 3 - Buffer slot + overbooking in the second half",
    idea="Slot 9 stays empty to absorb delays; overbooking is allowed only in slots 10-15.",
    n_slots=16,
    slot_min=15,
    threshold=0.30,
    blocked=(8,),
    overbook_slots=tuple(range(9, 15)),
    thresholds_to_try=(0.20, 0.25, 0.30, 0.40),
)

if __name__ == "__main__":
    print("Saved:", render_html(TEMPLATE))
