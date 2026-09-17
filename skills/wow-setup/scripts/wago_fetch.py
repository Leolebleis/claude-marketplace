#!/usr/bin/env python3
"""Fetch wago.io import strings and metadata without a browser.

Usage:
  wago_fetch.py info     <id-or-url>            # name, type, last modified, latest version
  wago_fetch.py versions <id-or-url>            # every version with its changelog
  wago_fetch.py raw      <id-or-url> [outfile]  # the import string (stdout or file)

<id-or-url> accepts "zaiOOdVa1", "https://wago.io/zaiOOdVa1" or a slug URL.
Uses the documented Wago API (https://data.wago.io/openapi.json). Stdlib only.
"""
import json
import re
import sys
import urllib.request

API = "https://data.wago.io"


def wago_id(s):
    m = re.search(r"wago\.io/([A-Za-z0-9_\-]+)", s)
    return m.group(1) if m else s.strip()


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wow-setup-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def info(wid):
    d = json.loads(get(f"{API}/lookup/wago?id={wid}"))
    versions = ((d.get("versions") or {}).get("versions") or [])
    latest = versions[0] if versions else {}
    desc = ((d.get("description") or {}).get("text") or "").strip()
    return {
        "id": d.get("_id"),
        "name": d.get("name"),
        "type": d.get("type"),
        "url": d.get("url"),
        "modified": (d.get("date") or {}).get("modified"),
        "author": (d.get("user") or {}).get("name"),
        "views": d.get("viewCount"),
        "latest_version": latest.get("versionString"),
        "latest_changelog": ((latest.get("changelog") or {}).get("text") if isinstance(latest.get("changelog"), dict) else latest.get("changelog")),
        "description": desc[:600],
    }


def raw(wid):
    return get(f"{API}/api/raw/encoded?id={wid}")


def versions(wid):
    d = json.loads(get(f"{API}/lookup/wago?id={wid}"))
    out = []
    for v in ((d.get("versions") or {}).get("versions") or []):
        cl = v.get("changelog")
        out.append({
            "version": v.get("versionString"),
            "date": v.get("date"),
            "changelog": (cl.get("text") if isinstance(cl, dict) else cl) or "",
        })
    return out


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # changelogs carry emoji
    except Exception:
        pass
    if len(argv) < 3 or argv[1] not in ("info", "raw", "versions"):
        print(__doc__)
        return 2
    wid = wago_id(argv[2])
    if argv[1] == "info":
        print(json.dumps(info(wid), indent=2))
        return 0
    if argv[1] == "versions":
        print(json.dumps(versions(wid), indent=2))
        return 0
    s = raw(wid)
    if len(argv) > 3:
        with open(argv[3], "w", encoding="utf-8", newline="\n") as f:
            f.write(s)
        print(f"wrote {len(s)} chars to {argv[3]}")
    else:
        sys.stdout.write(s)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
