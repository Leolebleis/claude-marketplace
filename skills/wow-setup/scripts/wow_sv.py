#!/usr/bin/env python3
"""Read WoW SavedVariables (.lua) files as data.

WoW saved variables are Lua table literals, NOT indented with tabs, so grep/awk
on indentation fails. This parses them properly (stdlib only).

Usage:
  wow_sv.py dump <file.lua> [key/path] [depth] [maxitems]   # readable tree
  wow_sv.py json <file.lua> [key/path]                       # JSON to stdout
  wow_sv.py keys <file.lua>                                  # top-level globals

Examples:
  wow_sv.py dump Plater.lua profileKeys 1          # which profile each character uses
  wow_sv.py dump Plater.lua "profiles/My Profile" 0 300
  wow_sv.py json OPie.lua ProfileStorage/default/Bindings
"""
import json
import re
import sys

NUM = re.compile(r'-?(?:\d+\.?\d*(?:[eE][-+]?\d+)?|\d*\.\d+|inf|nan)')
IDENT = re.compile(r'[A-Za-z_]\w*')
DIG = re.compile(r'\d{1,3}')
BS = chr(92)


class Parser:
    def __init__(self, text):
        self.t = text
        self.i = 0

    def ws(self):
        t = self.t
        while self.i < len(t):
            c = t[self.i]
            if c in ' \t\r\n':
                self.i += 1
            elif t.startswith('--', self.i):
                j = t.find('\n', self.i)
                self.i = len(t) if j < 0 else j
            else:
                break

    def val(self):
        self.ws()
        t = self.t
        c = t[self.i]
        if c == '{':
            return self.tbl()
        if c == '"':
            return self.str()
        for lit, v in (('true', True), ('false', False), ('nil', None)):
            if t.startswith(lit, self.i) and not IDENT.match(t, self.i + len(lit)):
                self.i += len(lit)
                return v
        m = NUM.match(t, self.i)
        if m:
            self.i = m.end()
            v = m.group()
            try:
                return int(v)
            except ValueError:
                try:
                    return float(v)
                except ValueError:
                    return v
        raise ValueError('bad token at %d: %r' % (self.i, t[self.i:self.i + 40]))

    def str(self):
        t = self.t
        self.i += 1
        out = []
        while True:
            c = t[self.i]
            if c == BS:
                n = t[self.i + 1]
                if n == 'n':
                    out.append('\n'); self.i += 2
                elif n.isdigit():
                    m = DIG.match(t, self.i + 1)
                    out.append(chr(int(m.group()))); self.i = m.end()
                else:
                    out.append(n); self.i += 2
            elif c == '"':
                self.i += 1
                return ''.join(out)
            else:
                out.append(c); self.i += 1

    def tbl(self):
        t = self.t
        self.i += 1
        d = {}
        n = 1
        while True:
            self.ws()
            if t[self.i] == '}':
                self.i += 1
                return d
            if t[self.i] == '[':
                self.i += 1
                k = self.val()
                self.ws(); self.i += 1  # ]
                self.ws(); self.i += 1  # =
                d[k] = self.val()
            else:
                m = IDENT.match(t, self.i)
                if m and t[m.end():m.end() + 2].lstrip().startswith('=') and m.group() not in ('true', 'false', 'nil'):
                    self.i = m.end(); self.ws(); self.i += 1
                    d[m.group()] = self.val()
                else:
                    d[n] = self.val(); n += 1
            self.ws()
            if t[self.i] in ',;':
                self.i += 1


def load(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    out = {}
    p = Parser(text)
    while True:
        p.ws()
        if p.i >= len(text):
            return out
        m = re.compile(r'([A-Za-z_]\w*)\s*=').match(text, p.i)
        if not m:
            raise ValueError('expected global assignment near: %r' % text[p.i:p.i + 40])
        p.i = m.end()
        out[m.group(1)] = p.val()


def get(d, *path):
    for p in path:
        if isinstance(d, dict) and p in d:
            d = d[p]
        elif isinstance(d, dict) and p.isdigit() and int(p) in d:
            d = d[int(p)]
        else:
            return None
    return d


def show(v, depth=1, maxitems=60, maxdepth=1):
    pad = '  ' * depth
    if not isinstance(v, dict):
        print(pad + repr(v)[:200])
        return
    for k, vv in list(v.items())[:maxitems]:
        if isinstance(vv, dict):
            print('%s%r -> table(%d)' % (pad, k, len(vv)))
            if depth < maxdepth:
                show(vv, depth + 1, maxitems, maxdepth)
        else:
            print('%s%r = %s' % (pad, k, repr(vv)[:120]))
    if len(v) > maxitems:
        print('%s... (%d more)' % (pad, len(v) - maxitems))


def main(argv):
    # Saved variables can contain bytes the game already mangled (U+FFFD);
    # a cp1252 console would crash on them.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    if len(argv) < 3 or argv[1] not in ('dump', 'json', 'keys'):
        print(__doc__)
        return 2
    data = load(argv[2])
    if argv[1] == 'keys':
        for k, v in data.items():
            print(k, 'table(%d)' % len(v) if isinstance(v, dict) else repr(v))
        return 0
    path = [p for p in (argv[3].split('/') if len(argv) > 3 else []) if p]
    if argv[1] == 'json':
        sub = {k: (get(v, *path) if path else v) for k, v in data.items()}
        print(json.dumps(sub, indent=2, default=str))
        return 0
    maxdepth = int(argv[4]) if len(argv) > 4 else 1
    maxitems = int(argv[5]) if len(argv) > 5 else 60
    for k, v in data.items():
        sub = get(v, *path) if path else v
        if sub is None:
            continue
        print('## %s%s' % (k, ('/' + '/'.join(path)) if path else ''))
        show(sub, 1, maxitems, maxdepth)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
