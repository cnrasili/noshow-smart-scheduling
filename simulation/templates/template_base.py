"""Appointment template definition and HTML renderer shared by the template files."""
from __future__ import annotations

import dataclasses
import html
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clinic_sim import Layout, Policy, SessionConfig, fixed_interval, threshold_rule  # noqa: E402

HTML_DIR = Path(__file__).parent / "html"
REQUESTS = 20                 # booking requests per session, identical for every template
SESSION_MIN = 240             # planned session length (minutes), identical for every template


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    idea: str
    n_slots: int
    slot_min: float
    threshold: float | None = None            # None = no overbooking
    blocked: tuple[int, ...] = ()             # buffer slots (stay empty)
    overbook_slots: tuple[int, ...] | None = None
    offset: float = 0.0                       # second patient starts this fraction of a slot later
    thresholds_to_try: tuple[float, ...] = ()  # candidate thresholds for tuning

    def config(self, base: SessionConfig | None = None) -> SessionConfig:
        return dataclasses.replace(base or SessionConfig(), n_slots=self.n_slots, slot_min=self.slot_min,
                                   requests=REQUESTS)

    def layout(self) -> Layout:
        return Layout(frozenset(self.blocked), None if self.overbook_slots is None else frozenset(self.overbook_slots),
                      self.offset)

    def policy(self) -> Policy:
        return fixed_interval() if self.threshold is None else threshold_rule(self.threshold)

    def with_threshold(self, t: float) -> "Template":
        return dataclasses.replace(self, threshold=t)

    def rules(self) -> list[str]:
        out = [f"{self.n_slots} slots x {self.slot_min:g} min = {self.n_slots * self.slot_min:g} min session"]
        if self.blocked:
            out.append("Buffer (no patient): slot " + ", ".join(str(b + 1) for b in self.blocked))
        if self.threshold is None:
            out.append("One patient per slot, no overbooking")
        else:
            out.append(f"Overbook a booked slot only if its patient has a no-show risk of at least {self.threshold:.2f} "
                       "(max 2 per slot, 4 overbooked slots per session)")
            if self.overbook_slots is not None:
                out.append(f"Overbooking allowed only in slots {min(self.overbook_slots) + 1}-{max(self.overbook_slots) + 1}")
            out.append("Second patient starts at the same time as the first" if self.offset == 0
                       else f"Second patient starts {self.offset * self.slot_min:g} min after the slot start")
        return out


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--mute:#667085;--line:#e4e7ec;--std:#cfe3f1;--ob:#f6c7b6;--buf:#e4e7ec;--acc:#2a6f97}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f141c;--card:#171e29;--ink:#e8ecf3;--mute:#93a0b4;--line:#2a3445;--std:#27506b;--ob:#8a4a36;--buf:#2a3445;--acc:#6bb1d8}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}main{max-width:1180px;margin:0 auto;padding:24px 16px}
h1{font-size:21px;margin:0}p{color:var(--mute)}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
.scroll{overflow-x:auto}.bar{position:relative;height:64px;margin-top:6px}
.slot{position:absolute;top:0;height:56px;border-radius:6px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.slot b{font-size:13px;position:relative;z-index:1}.std{background:var(--std)}.ob{background:var(--ob)}
.buffer{background:repeating-linear-gradient(45deg,var(--buf),var(--buf) 6px,transparent 6px,transparent 12px);border:1px dashed var(--mute)}
.slot i{position:absolute;bottom:0;right:0;height:14px;background:var(--acc);opacity:.55;border-radius:0 0 6px 6px}
.axis{position:relative;height:20px;font-size:11px;color:var(--mute)}.backbtn{display:inline-block;margin-bottom:14px;padding:6px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--acc,var(--accent,#2a6f97));text-decoration:none;font-size:14px}.backbtn:hover{opacity:.8}.axis span{position:absolute;top:0;transform:translateX(-50%)}
.legend span{display:inline-block;margin-right:16px;font-size:13px}.legend em{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:6px}
"""


def render_html(t: Template, path: Path | None = None, note: str = "", back: tuple[str, str] = ("../../output/templates_hub.html", "Templates")) -> Path:
    """Write a self-contained HTML picture of the template."""
    scale = 4.2  # px per minute
    cells = []
    for s in range(t.n_slots):
        x, w = s * t.slot_min * scale, t.slot_min * scale
        if s in t.blocked:
            cls, label = "buffer", "buffer"
        elif t.threshold is not None and (t.overbook_slots is None or s in t.overbook_slots):
            cls, label = "ob", str(s + 1)
        else:
            cls, label = "std", str(s + 1)
        extra = ""
        if cls == "ob":
            ox = t.offset * w
            extra = f'<i style="left:{ox:.0f}px" title="second patient starts here"></i>'
        cells.append(f'<div class="slot {cls}" style="left:{x:.0f}px;width:{w - 2:.0f}px"><b>{label}</b>{extra}</div>')
    ticks = "".join(f'<span style="left:{m * scale:.0f}px">{m}</span>'
                    for m in range(0, int(t.n_slots * t.slot_min) + 1, 60))
    width = t.n_slots * t.slot_min * scale
    rules = "".join(f"<li>{html.escape(r)}</li>" for r in t.rules())
    banner = f'<div class="card"><b>{html.escape(note)}</b></div>' if note else ""
    doc = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(t.name)}</title><style>{CSS}</style></head><body><main>"
        f'<a class="backbtn" href="{back[0]}">&larr; Back to {back[1]}</a>'
        f"<h1>{html.escape(t.name)}</h1><p>{html.escape(t.idea)}</p>{banner}"
        f'<div class="card"><div class="scroll"><div style="width:{width:.0f}px">'
        f'<div class="bar">{"".join(cells)}</div><div class="axis">{ticks}</div></div></div>'
        '<div class="legend"><span><em style="background:var(--std)"></em>single-booking slot</span>'
        '<span><em style="background:var(--ob)"></em>slot where overbooking is allowed</span>'
        '<span><em style="background:var(--buf);border:1px dashed var(--mute)"></em>buffer</span>'
        '<span><em style="background:var(--acc);opacity:.55"></em>start of the second patient</span></div>'
        '<small style="color:var(--mute)">Minutes since session start</small></div>'
        f'<div class="card"><b>Rules</b><ul>{rules}</ul></div></main></body></html>'
    )
    path = path or HTML_DIR / f"{t.key}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    return path
