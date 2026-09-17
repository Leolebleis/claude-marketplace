#!/usr/bin/env python3
"""Rescale a Blizzard Edit Mode layout export for a different UI Scale.

Edit Mode offsets are in UI units. The UI space is always 768 / uiScale units
tall regardless of screen resolution, so a layout made at one UI scale lands
wrong at another: offsets overshoot or bunch up. Multiplying every offset by
(source_scale / target_scale) restores the author's proportions. Frames keep
their own size in units, so at a larger target scale they render bigger and
may touch; fine-tune the few that do in Edit Mode.

Usage:
  editmode_rescale.py <layout.txt> <source_uiScale> <target_uiScale> [out.txt]

Example (PanzaUI made at 0.65, you want 0.80):
  editmode_rescale.py 10-editmode-panzaui.txt 0.65 0.80 10b-editmode-panzaui-0.80.txt
"""
import re
import sys

# "<anchor> <relAnchor> <FrameName> <x> <y> -1" is how each system's position is stored.
POS = re.compile(r'(\b[A-Za-z_][A-Za-z0-9_]*) (-?\d+\.\d+) (-?\d+\.\d+) (-1\b)')


def rescale(text, factor):
    def repl(m):
        x = float(m.group(2)) * factor
        y = float(m.group(3)) * factor
        return f"{m.group(1)} {x:.1f} {y:.1f} {m.group(4)}"
    return POS.subn(repl, text)


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    src, s_scale, t_scale = argv[1], float(argv[2]), float(argv[3])
    factor = s_scale / t_scale
    text = open(src, encoding="utf-8").read().strip()
    out, n = rescale(text, factor)
    if len(argv) > 4:
        with open(argv[4], "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        print(f"rescaled {n} positions by {factor:.4f} -> {argv[4]}")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
