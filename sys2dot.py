#!/usr/bin/env python3

# sys2dot.py:     SIGNET CONNECTIONS TO GRAPHVIZ DOT
# AUTHOR:         DANIEL DESAI
# UPDATED:        2026-11-16
# VERSION:        26.b.0.1.6
#
# signet script.sg --connections | python3 sys2dot.py | dot -Tsvg -o system.svg

import json, sys

print("digraph signet {\n  rankdir=LR; node [shape=box];")
for c in json.load(sys.stdin):
    dst = c["module"]
    for ref in c["refs"]:
        src, port = ref.split(".")[:2]
        dash = ", style=dashed" if ref in c.get("stepped", ()) else ""
        print(f'  "{src}" -> "{dst}" [label="{port} → {c["port"]}"{dash}];')
    for k in c["constants"]:
        node = f'{dst}.{c["port"]}={k}'  # One node per use
        print(f'  "{node}" [label="{k}", shape=plaintext];')
        print(f'  "{node}" -> "{dst}" [label="{c["port"]}"];')
print("}")
