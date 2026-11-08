#!/usr/bin/env python3

# visualizer.py:  SIGNET SYSTEM DIAGRAMS AS SVG
# AUTHOR:         DANIEL DESAI
# UPDATED:        2026-11-08
# VERSION:        26.b.0.1.4
#

"""
Draws the system a Signet script wires up, the way Starfire's System view does, as one SVG file.
Standard library only; needs signet.py in the same folder. Run it in the folder the script runs in:
a line is solid amber where its source .sig exists, faint where it has no data yet.

    python3 visualizer.py <signet code>.signet [-o <diagram>.svg] [--theme light|dark] [--large]
                                        [--label <module>=<N>:<module> --label <module>=<N>:<module>]

Modules have inputs on the left and outputs on the right; "= value" is a constant from the script.
A dashed line carries a value from the pass before (a stepped loop) and runs back under the boxes.
"""

import argparse
import os
import sys
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import signet

BW, BUSW, HEAD, ROW, GAPX, GAPY, PAD = 200, 70, 26, 18, 110, 28, 24
LANE = 10
SETBACK = 8 + 2 * 10    # Arrowhead, then two 6-on 4-off dashes before a lane turns up to its port

THEMES = {          # Starfire's print and screen colors
    "light": dict(bg="#ffffff", box="#ffffff", edge="#8fb6d6", label="#000000", port="#222222",
                  const="#618a6b", dot="#405a3a", line="#FFB300"),
    "dark": dict(bg="#0c0e0c", box="#080908", edge="#0077C8", label="#00A3E0", port="#b8ffd0",
                 const="#618a6b", dot="#405a3a", line="#FFB300"),
}


def graph(path: str) -> dict:
    """Boxes and lines for the script at path, from its connect()s and the .sig files beside it."""
    code = open(path, encoding="utf-8").read()
    conns = signet.connections(code, points=True)
    folder = os.path.dirname(os.path.abspath(path))
    boxes, lines = {}, []

    def box(key, **kw):
        if key not in boxes:
            boxes[key] = dict(id=f"b{len(boxes)}", inputs=[], outputs=[], **kw)
        return boxes[key]

    def port(lst, name, **kw):
        for p in lst:
            if p["port"] == name:
                return p
        lst.append(dict(port=name, **kw))
        return lst[-1]

    def has_data(fname):
        try:
            signet.stream_sig(fname) or signet.read_sig(fname)    # A stream still being written counts
            return True
        except (ValueError, OSError):
            return False

    def source(ref):
        fname = os.path.join(folder, ref)
        parts = ref[:-4].split(".") if ref.endswith(".sig") else []
        if len(parts) == 2:                         # module.port.sig
            b = box(("m", parts[0]), kind="module", module=parts[0], label=parts[0])
            port(b["outputs"], parts[1])
            return b, parts[1], "amber" if has_data(fname) else "dim", ref
        b = box(("f", ref), kind="file", label=ref)
        port(b["outputs"], ref)
        return b, ref, "amber" if os.path.exists(fname) else "dim", ref

    for cn in conns:
        stem, inp = cn["module"], cn["port"]
        if not stem:                                # connect(x, 20:volts) needs Starfire's points
            continue
        dst = box(("m", stem), kind="module", module=stem, label=stem)
        ip = port(dst["inputs"], inp)
        refs, consts, buses = cn["refs"], cn["constants"], cn["buses"]
        if consts and not refs and not buses:
            have = ip["const"].split(", ") if ip.get("const") else []
            ip["const"] = ", ".join(have + [c for c in consts if c not in have])
        stepped = cn.get("stepped", ())
        for ref in refs:
            b, prt, color, src = source(ref)
            lines.append(dict(frm=b["id"], fport=prt, to=dst["id"], tport=inp, color=color, source=src,
                              stepped=ref in stepped, bus=False))
        for bundle in buses:
            jb = box(("j", cn["line"], inp), kind="bus", label="mux")
            worst = "amber"
            for fld, rs in bundle:
                port(jb["inputs"], fld)
                for ref in rs:
                    b, prt, color, src = source(ref)
                    lines.append(dict(frm=b["id"], fport=prt, to=jb["id"], tport=fld, color=color, source=src,
                                      stepped=False, bus=False))
                    worst = "dim" if color == "dim" else worst
            port(jb["outputs"], "bus")
            lines.append(dict(frm=jb["id"], fport="bus", to=dst["id"], tport=inp, color=worst,
                              source="multiplex", stepped=False, bus=True))

    for b in list(boxes.values()):                  # Outputs already on disk, connected or not
        if b["kind"] == "module":
            for n in sorted(os.listdir(folder)):
                if n.startswith(b["module"] + ".") and n.endswith(".sig") and n.count(".") == 2:
                    port(b["outputs"], n.split(".")[1])
    return {"boxes": list(boxes.values()), "lines": lines}


def back_lines(boxes, lines, index) -> set:
    """Indexes of the lines that close a loop with no stepped line to break it (depth-first, in box order)."""
    after = {b["id"]: [] for b in boxes}
    for k, ln in zip(index, lines):
        after[ln["frm"]].append((k, ln["to"]))
    state, back = {}, set()

    def visit(n):
        state[n] = 1
        for k, m in after[n]:
            if state.get(m) == 1:
                back.add(k)
            elif m not in state:
                visit(m)
        state[n] = 2
    for b in boxes:
        if b["id"] not in state:
            visit(b["id"])
    return back


def svg(g: dict, theme: str = "light", large: bool = False) -> str:
    """The diagram. Columns follow the data; a line that skips columns runs through a slot in each,
    and a line from the pass before runs back under the boxes in its source's lane."""
    boxes = [dict(b) for b in g["boxes"]]
    by_id = {b["id"]: b for b in boxes}
    lines = g["lines"]
    back = {k for k, ln in enumerate(lines) if ln["stepped"]}
    rest = [k for k in range(len(lines)) if k not in back]
    back |= back_lines(boxes, [lines[k] for k in rest], rest)
    layer = {b["id"]: 0 for b in boxes}
    for _ in range(len(boxes)):
        moved = False
        for k, ln in enumerate(lines):
            if k not in back and ln["frm"] != ln["to"] and layer[ln["to"]] < layer[ln["frm"]] + 1:
                layer[ln["to"]] = layer[ln["frm"]] + 1
                moved = True
        if not moved:
            break
    cols = {}
    for b in boxes:
        b["w"] = BUSW if b["kind"] == "bus" else BW
        b["h"] = HEAD + max(len(b["inputs"]), len(b["outputs"]), 1) * ROW + 8
        cols.setdefault(layer[b["id"]], []).append(b)
    vias = []
    for k, ln in enumerate(lines):
        v = []
        for c in range(layer[ln["frm"]] + 1, layer[ln["to"]]) if k not in back else ():
            slot = {"slot": True, "w": BW, "h": 10, "label": "", "kind": "slot"}
            cols.setdefault(c, []).append(slot)
            v.append(slot)
        vias.append(v)
    lane_of = {}
    for k in sorted(back):
        lane_of.setdefault((lines[k]["frm"], lines[k]["fport"]), len(lane_of))
    left = max(PAD, 3 + SETBACK + 5 * min(len(lane_of) - 1, 3) + 6) if lane_of else PAD
    width = height = 0
    for c, col in cols.items():
        col.sort(key=lambda b: (2 if b.get("slot") else 0 if b["kind"] == "module" else 1, b["label"]))
        y = PAD
        for b in col:
            b["x"], b["y"] = left + c * (BW + GAPX), y
            y += b["h"] + GAPY
        width = max(width, left + c * (BW + GAPX) + BW + PAD)
        height = max(height, y + PAD)
    lanes = height - GAPY
    height += LANE * len(lane_of)
    width, height = max(width, 300), max(height, 120)

    def port_y(b, lst, name):
        i = next((k for k, p in enumerate(lst) if p["port"] == name), 0)
        return b["y"] + HEAD + i * ROW + ROW / 2

    size = (15, 14) if large else (12, 11)          # Large: about 10 pt when the figure is 5.5 in wide
    out = []
    for i, (ln, via) in enumerate(zip(lines, vias)):
        a, b = by_id[ln["frm"]], by_id[ln["to"]]
        pts = [(a["x"] + a["w"], port_y(a, a["outputs"], ln["fport"]))]
        for v in via:
            pts += [(v["x"], v["y"] + v["h"] / 2), (v["x"] + v["w"], v["y"] + v["h"] / 2)]
        pts.append((b["x"] - 3, port_y(b, b["inputs"], ln["tport"])))      # Arrow tip at the port
        if i in back:
            (ax, ay), (bx, by) = pts[0], pts[-1]
            j = lane_of[(ln["frm"], ln["fport"])]
            ly, jog = lanes + LANE * (j + 0.5), 5 * (j % 4)
            d = f"M{ax:.0f},{ay:.0f} H{ax + 6 + jog:.0f} V{ly:.0f} H{bx - SETBACK - jog:.0f} V{by:.0f} H{bx:.0f}"
        else:
            d = f"M{pts[0][0]:.0f},{pts[0][1]:.0f}"
            for k in range(1, len(pts)):
                (ax, ay), (bx, by) = pts[k - 1], pts[k]
                if k % 2 == 0 and via:      # Straight across a slot
                    d += f" L{bx:.0f},{by:.0f}"
                    continue
                dx = max(40, (bx - ax) / 2) if bx > ax else 90
                d += f" C{ax + dx:.0f},{ay:.0f} {bx - dx:.0f},{by:.0f} {bx:.0f},{by:.0f}"
        cls = "line " + ln["color"] + (" bus" if ln["bus"] else "") + (" stepped" if ln["stepped"] else "")
        tip = f'{ln["source"]} → {b["label"]}.{ln["tport"]}' + (", from the pass before" if ln["stepped"] else "")
        out.append(f'<path class="{cls}" d="{d}" marker-end="url(#arrow)"><title>{escape(tip)}</title></path>')
    for b in by_id.values():
        if b.get("slot"):
            continue
        x, y, w = b["x"], b["y"], b["w"]
        parts = [f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{b["h"]}" rx="5"/>'
                 f'<text class="label" x="{x + 8}" y="{y + 17}">{escape(b["label"])}</text>']
        for k, p in enumerate(b["inputs"]):
            py = y + HEAD + k * ROW + ROW / 2
            const = ""
            if p.get("const"):                      # Shortened to clear the output name on its row
                outs = b["outputs"][k]["port"] if b["kind"] != "bus" and k < len(b["outputs"]) else ""
                room = int((w - 16) / (0.66 * size[1])) - len(p["port"]) - 3 - (len(outs) + 2 if outs else 0)
                c = p["const"] if len(p["const"]) <= room else p["const"][:max(room - 1, 1)] + "…"
                const = f' <tspan class="const">= {escape(c)}</tspan>'
            parts.append(f'<circle class="dot" cx="{x}" cy="{py:.0f}" r="3"/>'
                         f'<text class="port" x="{x + 8}" y="{py + 4:.0f}">{escape(p["port"])}{const}</text>')
        if b["kind"] != "bus":
            for k, p in enumerate(b["outputs"]):
                py = y + HEAD + k * ROW + ROW / 2
                parts.append(f'<circle class="dot" cx="{x + w}" cy="{py:.0f}" r="3"/>'
                             f'<text class="port" x="{x + w - 8}" y="{py + 4:.0f}" text-anchor="end">{escape(p["port"])}</text>')
        out.append("<g>" + "".join(parts) + "</g>")
    t = THEMES[theme]
    style = (f"text{{font-family:'B612 Mono','SF Mono',Menlo,Consolas,monospace}}"
             f".box{{fill:{t['box']};stroke:{t['edge']};stroke-width:1.5}}"
             f".label{{fill:{t['label']};font-size:{size[0]}px;font-weight:700}}"
             f".port{{fill:{t['port']};font-size:{size[1]}px}}.const{{fill:{t['const']}}}.dot{{fill:{t['dot']}}}"
             f".line{{fill:none;stroke:{t['line']};stroke-width:2}}.line.dim{{opacity:.4}}.line.bus{{stroke-width:4}}"
             f".line.stepped{{stroke-dasharray:6 4}}.head{{fill:{t['line']}}}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
            f'<style>{style}</style><defs><marker id="arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="8" '
            f'markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path class="head" d="M0,0 L8,4 L0,8 z"/>'
            f'</marker></defs><rect width="100%" height="100%" fill="{t["bg"]}"/>{"".join(out)}</svg>\n')


def main():
    ap = argparse.ArgumentParser(description="Draw a Signet script's system as SVG, without Starfire.")
    ap.add_argument("script", help="a .signet file, run from its own folder")
    ap.add_argument("-o", "--out", help="SVG file to write (default: the script's name, .svg)")
    ap.add_argument("--theme", choices=THEMES, default="light")
    ap.add_argument("--large", action="store_true", help="bigger text, for print")
    ap.add_argument("--label", action="append", default=[], metavar="MODULE=TEXT", help="a box's title")
    a = ap.parse_args()
    try:
        g = graph(a.script)
    except (OSError, ValueError) as e:
        sys.exit(f"visualizer: {e}")
    names = dict(s.split("=", 1) for s in a.label)
    for b in g["boxes"]:
        b["label"] = names.get(b.get("module", ""), b["label"])
    title = {b["id"]: b["label"] for b in g["boxes"]}
    for ln in g["lines"]:
        print(f'{ln["source"]:<24} → {title[ln["to"]]}.{ln["tport"]}' + ("   (pass before)" if ln["stepped"] else ""))
    out = a.out or os.path.splitext(a.script)[0] + ".svg"
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg(g, a.theme, a.large))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()