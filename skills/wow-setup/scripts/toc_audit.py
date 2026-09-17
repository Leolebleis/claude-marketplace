#!/usr/bin/env python3
"""Audit installed addons against the client build.

Usage:
  toc_audit.py <path-to-_retail_> [--all]

Prints one line per addon folder: interface values found in every .toc in the
folder, whether any value is current, and which characters have it enabled.
Without --all only out-of-date addons are printed. An addon counts as enabled
for a character when AddOns.txt says so, or when it is absent from AddOns.txt
and its TOC DefaultState is not "disabled" (Blizzard's rule for the
"interface modifications which are out of date" prompt).
"""
import glob
import os
import re
import sys


def client_interface(retail):
    info = os.path.join(os.path.dirname(retail.rstrip("\\/")), ".build.info")
    with open(info, encoding="utf-8", errors="replace") as f:
        header = f.readline().split("|")
        row = f.readline().split("|")
    vi = next(i for i, h in enumerate(header) if h.startswith("Version"))
    major, minor, patch = row[vi].split(".")[:3]
    return int(major) * 10000 + int(minor) * 100 + int(patch), row[vi]


def toc_fields(path):
    ifaces, default_state = [], "enabled"
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"##\s*Interface:\s*(.+)", line)
            if m:
                ifaces += [int(x) for x in re.findall(r"\d+", m.group(1))]
            m = re.match(r"##\s*DefaultState:\s*(\w+)", line, re.I)
            if m:
                default_state = m.group(1).lower()
    return ifaces, default_state


def addons_txt(retail):
    out = {}
    for p in glob.glob(os.path.join(retail, "WTF", "Account", "*", "*", "*", "AddOns.txt")):
        parts = p.replace("\\", "/").split("/")
        char = f"{parts[-3]}/{parts[-2]}"
        d = {}
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if ":" in line:
                    name, state = line.rstrip("\r\n").split(":", 1)
                    d[name.strip()] = state.strip()
        out[char] = d
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    retail = argv[1]
    show_all = "--all" in argv
    current, version = client_interface(retail)
    chars = addons_txt(retail)
    print(f"client {version} = interface {current}; {len(chars)} character AddOns.txt files")
    for folder in sorted(glob.glob(os.path.join(retail, "Interface", "AddOns", "*"))):
        name = os.path.basename(folder)
        tocs = glob.glob(os.path.join(folder, "*.toc"))
        if not tocs:
            continue
        ifaces, default_state = [], "enabled"
        for t in tocs:
            i, ds = toc_fields(t)
            ifaces += i
            default_state = ds
        ok = any(v >= current for v in ifaces)
        enabled_on = [c for c, d in chars.items()
                      if d.get(name, default_state) == "enabled"]
        if ok and not show_all:
            continue
        flag = "ok " if ok else "OUT"
        print(f"{flag} {name:40s} interface={sorted(set(ifaces))} enabled_on={len(enabled_on)}"
              + ("" if ok else f" -> {', '.join(sorted(enabled_on)) or 'nobody'}"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
