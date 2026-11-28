"""Interdigitated electrode generator for convex outlines. Units: mm.

Exports PDF, SVG, EPS, PNG, JPG, TIFF, DXF, Gerber, GDSII and CSV.
"""
import math
import os
import struct

import matplotlib.pyplot as plt

MAX_SIZE = 500.0      # largest coordinate or dimension accepted (mm)
MIN_FEATURE = 0.01    # smallest finger, gap or busbar accepted (mm)
MARGIN = 5.0          # white border on drawings (mm)

def is_convex(pts):
    """True if the outline has area, no dents and no crossing edges."""
    turns, total = [], 0.0
    n = len(pts)
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        ux, uy, vx, vy = bx - ax, by - ay, cx - bx, cy - by
        cross, dot = ux * vy - uy * vx, ux * vx + uy * vy
        total += math.atan2(cross, dot)
        if abs(cross) > 1e-9:
            turns.append(cross > 0)
    return len(set(turns)) == 1 and abs(abs(total) - 2 * math.pi) < 1e-6

def ask_points():
    print("Enter the corners in order around the edge as x,y in mm.")
    print("Press Enter on an empty line when finished.")
    pts = []
    while True:
        text = input(f"Corner {len(pts) + 1}: ").strip()
        if text == "":
            if len(pts) > 1 and pts[0] == pts[-1]:
                pts.pop()                      # first corner was repeated
            if len(pts) >= 3 and is_convex(pts):
                return pts
            print("Need 3+ different corners, in order, with no dents. Start again.")
            pts = []
            continue
        try:
            x, y = (float(v) for v in text.split(","))
        except ValueError:
            print("Type two numbers with a comma, e.g. 2.5,4")
            continue
        if not (abs(x) <= MAX_SIZE and abs(y) <= MAX_SIZE):
            print(f"Values must be between -{MAX_SIZE:g} and {MAX_SIZE:g}.")
        elif pts and pts[-1] == (x, y):
            print("Same as the previous corner, ignored.")
        else:
            pts.append((x, y))

def ask(prompt, default):
    while True:
        text = input(f"{prompt} [{default}]: ").strip()
        try:
            value = float(text) if text else default
        except ValueError:
            value = None
        if value is not None and MIN_FEATURE <= value <= MAX_SIZE:
            return value
        print(f"Enter a number from {MIN_FEATURE} to {MAX_SIZE:g} (use a dot).")

def edges_at(pts, y):
    """Left and right x of the outline at height y."""
    xs = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if y1 != y2 and min(y1, y2) <= y <= max(y1, y2):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    return min(xs), max(xs)

def levels(pts, y0, y1):
    """Heights to sample: both ends, any corners between, and fine steps."""
    steps = [y0 + (y1 - y0) * k / 50 for k in range(51)]
    return sorted(set(steps + [y for _, y in pts if y0 < y < y1]))

def band(ys, x_start, x_end):
    """Polygon between two x(y) curves."""
    return ([(x_start(y), y) for y in ys] +
            [(x_end(y), y) for y in reversed(ys)])

def distance(p, q):
    """Smallest distance between the edges of two polygons that do not cross."""
    best = math.inf
    for points, poly in ((p, q), (q, p)):
        for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
            dx, dy = bx - ax, by - ay
            length = dx * dx + dy * dy
            for x, y in points:
                t = ((x - ax) * dx + (y - ay) * dy) / length if length else 0
                t = max(0, min(1, t))
                best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best

def fill(pts, width, gap, busbar):
    low = min(y for _, y in pts)
    high = max(y for _, y in pts)
    L = lambda y: edges_at(pts, y)[0]
    R = lambda y: edges_at(pts, y)[1]

    # use only heights where the two busbars stay at least one gap apart
    samples = [low + (high - low) * k / 2000 for k in range(2001)]
    extra = 0.0
    while True:
        need = 2 * busbar + 2 * gap + extra
        usable = [y for y in samples if R(y) - L(y) >= need]
        if not usable:
            raise ValueError("Outline is too narrow. Reduce busbar or gap.")
        y0, y1 = usable[0], usable[-1]
        ys = levels(pts, y0, y1)
        left_bar = band(ys, L, lambda y: L(y) + busbar)
        right_bar = band(ys, lambda y: R(y) - busbar, R)
        if distance(left_bar, right_bar) >= gap - 1e-6:
            break
        extra += gap / 5
    a = [left_bar]       # left electrode
    b = [right_bar]      # right electrode

    y, i = y0 + gap, 0
    while y + width <= y1 - gap:
        fy = levels(pts, y, y + width)
        other = (lambda t: R(t) - busbar) if i % 2 == 0 else (lambda t: L(t) + busbar)
        # slanted busbars need a longer horizontal clearance
        lo, hi = max(y0, y - gap), min(y1, y + width + gap)
        h = (hi - lo) / 20
        slope = max(abs(other(lo + (k + 1) * h) - other(lo + k * h)) / h
                    for k in range(20))
        clear = gap * math.hypot(1, slope)
        side = i % 2
        own = a if side == 0 else b
        other_bus = (b if side == 0 else a)[0]
        # shorten the finger until it really is one gap from the other busbar
        while True:
            if side == 0:
                start, end = (lambda t: L(t) + busbar), (lambda t: other(t) - clear)
            else:
                start, end = (lambda t: other(t) + clear), (lambda t: R(t) - busbar)
            if not all(end(t) - start(t) >= width for t in fy):
                break
            finger = band(fy, start, end)
            if distance(finger, other_bus) >= gap - 1e-6:
                own.append(finger)
                break
            clear += gap / 20
        y += width + gap
        i += 1
    if len(a) < 2 or len(b) < 2:
        raise ValueError("No room for fingers on both sides. Reduce the sizes.")
    return a, b

def outlines(a, b):
    """Join busbar and fingers into ONE closed outline per electrode."""
    # left electrode: up the outer edge, then down the inner edge
    bus, n = a[0], len(a[0]) // 2
    outer, inner = bus[:n], bus[n:]
    left, top = list(outer), float("inf")
    for f in sorted(a[1:], key=lambda f: f[0][1], reverse=True):
        m = len(f) // 2
        y_low, y_high = f[0][1], f[m - 1][1]
        left += [p for p in inner if y_high < p[1] < top]
        left += [f[m - 1]] + f[m:] + [f[0]]
        top = y_low
    left += [p for p in inner if p[1] < top]

    # right electrode: up the inner edge, then down the outer edge
    bus, n = b[0], len(b[0]) // 2
    inner, outer = bus[:n], bus[n:]
    right, bottom = [], float("-inf")
    for f in sorted(b[1:], key=lambda f: f[0][1]):
        m = len(f) // 2
        y_low, y_high = f[0][1], f[m - 1][1]
        right += [p for p in inner if bottom < p[1] < y_low]
        right += [f[-1]] + f[:m] + [f[m]]
        bottom = y_high
    right += [p for p in inner if p[1] > bottom]
    right += outer
    return [left, right]

def save_dxf(path, shapes):
    """DXF (R12), units mm, one closed polyline per electrode."""
    d = [0, "SECTION", 2, "HEADER", 9, "$ACADVER", 1, "AC1009",
         9, "$INSUNITS", 70, 4, 0, "ENDSEC", 0, "SECTION", 2, "ENTITIES"]
    for k, shape in enumerate(shapes, 1):
        layer = f"ELECTRODE{k}"
        d += [0, "POLYLINE", 8, layer, 66, 1, 70, 1]
        for x, y in shape:
            d += [0, "VERTEX", 8, layer, 10, f"{x:.6f}", 20, f"{y:.6f}"]
        d += [0, "SEQEND", 8, layer]
    d += [0, "ENDSEC", 0, "EOF"]
    with open(path, "w") as file:
        file.write("\n".join(map(str, d)) + "\n")

def save_gerber(path, shapes):
    """Gerber (RS-274X), units mm, copper image only."""
    def xy(p):
        return f"X{round(p[0] * 1e6)}Y{round(p[1] * 1e6)}"
    g = ["%FSLAX46Y46*%", "%MOMM*%", "%LPD*%", "G01*"]
    for shape in shapes:
        g += ["G36*", xy(shape[0]) + "D02*"]
        g += [xy(p) + "D01*" for p in shape[1:] + shape[:1]]
        g += ["G37*"]
    g += ["M02*"]
    with open(path, "w") as file:
        file.write("\n".join(g) + "\n")

def save_gds(path, shapes):
    """GDSII, user unit 1 um, database unit 1 nm, layer 1."""
    def record(code, data=b""):
        return struct.pack(">HH", len(data) + 4, code) + data

    def real8(v):                      # GDSII's own number format
        exp = 64
        while v >= 1:
            v, exp = v / 16, exp + 1
        while v < 1 / 16:
            v, exp = v * 16, exp - 1
        return struct.pack(">Q", (exp << 56) | int(v * 2 ** 56))

    date = struct.pack(">12h", *([2026, 1, 1, 0, 0, 0] * 2))
    out = record(0x0002, struct.pack(">h", 600)) + record(0x0102, date)
    out += record(0x0206, b"IDELIB")
    out += record(0x0305, real8(1e-3) + real8(1e-9))
    out += record(0x0502, date) + record(0x0606, b"IDE\0")
    for shape in shapes:
        pts = [(round(x * 1e6), round(y * 1e6)) for x, y in shape + shape[:1]]
        if len(pts) > 8191:
            raise SystemExit("Too many points for GDS. Use fewer fingers.")
        out += record(0x0800) + record(0x0D02, struct.pack(">h", 1))
        out += record(0x0E02, struct.pack(">h", 0))
        out += record(0x1003, b"".join(struct.pack(">ii", *p) for p in pts))
        out += record(0x1100)
    out += record(0x0700) + record(0x0400)
    with open(path, "wb") as file:
        file.write(out)

IMAGES = ["pdf", "svg", "eps", "ps", "png", "jpg", "tif"]
CAD = {"dxf": save_dxf, "gbr": save_gerber, "gds": save_gds}
FORMATS = IMAGES + list(CAD)

def clean(poly):
    """Drop repeated and in-between points on straight edges."""
    out = []
    for p in poly:
        p = (round(p[0], 6), round(p[1], 6))
        if not out or p != out[-1]:
            out.append(p)
    if out[0] == out[-1]:
        out.pop()
    i = 0
    while i < len(out) and len(out) > 3:
        (ax, ay), (bx, by), (cx, cy) = out[i - 1], out[i], out[(i + 1) % len(out)]
        if abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) < 1e-7:
            del out[i]
            i = max(i - 1, 0)
        else:
            i += 1
    return out

def merge(parts, left_side):
    """Join one busbar and its fingers into a single outline."""
    bus, fingers = parts[0], parts[1:]
    half = len(bus) // 2
    if left_side:        # outer edge bottom to top, inner edge top to bottom
        outer, inner = bus[:half], bus[half:]
    else:
        outer, inner = bus[half:][::-1], bus[:half][::-1]
    path, remaining = list(outer), list(inner)
    for f in sorted(fingers, key=lambda f: -f[0][1]):
        n = len(f) // 2
        start, end = f[:n], f[n:][::-1]          # both run bottom to top
        base, tip = (start, end) if left_side else (end, start)
        low, high = base[0][1], base[-1][1]
        path += [p for p in remaining if p[1] > high]
        path += base[-1:] + tip[::-1] + base[:1]
        remaining = [p for p in remaining if p[1] < low]
    return clean(path + remaining)

def bounds(polys):
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)

def save_drawing(path, polys, ext):
    """Black on white at true size."""
    x0, y0, x1, y1 = bounds(polys)
    w, h = x1 - x0 + 2 * MARGIN, y1 - y0 + 2 * MARGIN
    fig = plt.figure(figsize=(w / 25.4, h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0 - MARGIN, x1 + MARGIN)
    ax.set_ylim(y0 - MARGIN, y1 + MARGIN)
    ax.axis("off")
    for p in polys:
        ax.fill(*zip(*p), color="black", linewidth=0)
    # 1200 dpi, lowered for large designs so memory does not run out
    dpi = int(min(1200, 8000 / (max(w, h) / 25.4)))
    try:
        fig.savefig(path, format=ext, dpi=dpi)
    finally:
        plt.close(fig)
    if ext in ("png", "jpg", "tiff"):
        print(f"  image resolution: {dpi} dpi")

def save_dxf(path, polys):
    """DXF R12: one closed outline per electrode, drawn in mm."""
    out = ["0", "SECTION", "2", "ENTITIES"]
    for layer, p in enumerate(polys, 1):
        name = f"ELECTRODE{layer}"
        out += ["0", "POLYLINE", "8", name, "66", "1", "70", "1",
                "10", "0.0", "20", "0.0", "30", "0.0"]
        for x, y in p:
            out += ["0", "VERTEX", "8", name, "10", f"{x:.6f}",
                    "20", f"{y:.6f}", "30", "0.0"]
        out += ["0", "SEQEND", "8", name]
    out += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(out) + "\n")

def save_gerber(path, polys):
    """Gerber RS-274X, mm, one filled region per electrode."""
    xy = lambda x, y: f"X{round(x * 1e6)}Y{round(y * 1e6)}"
    out = ["%FSLAX46Y46*%", "%MOMM*%", "%LPD*%", "G01*"]
    for p in polys:
        out += ["G36*", xy(*p[0]) + "D02*"]
        out += [xy(*q) + "D01*" for q in p[1:] + p[:1]]
        out += ["G37*"]
    out += ["M02*"]
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(out) + "\n")

def gds_real(value):
    """GDSII 8-byte floating point number (base 16)."""
    if value == 0:
        return bytes(8)
    exponent = 64
    while value >= 1:
        value /= 16
        exponent += 1
    while value < 1 / 16:
        value *= 16
        exponent -= 1
    return bytes([exponent]) + int(value * 2**56).to_bytes(7, "big")

def save_gds(path, polys):
    """GDSII: layers 1 and 2, database unit 1 nm."""
    def record(kind, data=b""):
        return struct.pack(">HH", len(data) + 4, kind) + data
    if any(len(p) > 8000 for p in polys):
        raise ValueError("Too many points for GDSII. Use fewer fingers.")
    date = struct.pack(">12h", *([2000, 1, 1, 0, 0, 0] * 2))
    data = record(0x0002, struct.pack(">h", 600))
    data += record(0x0102, date) + record(0x0206, b"IDE\0")
    data += record(0x0305, gds_real(1e-3) + gds_real(1e-9))
    data += record(0x0502, date) + record(0x0606, b"ELECTRODE\0")
    for layer, p in enumerate(polys, 1):
        ring = p + p[:1]
        coords = [round(v * 1e6) for point in ring for v in point]
        data += record(0x0800) + record(0x0D02, struct.pack(">h", layer))
        data += record(0x0E02, struct.pack(">h", 0))
        data += record(0x1003, struct.pack(f">{len(coords)}i", *coords))
        data += record(0x1100)
    data += record(0x0700) + record(0x0400)
    with open(path, "wb") as f:
        f.write(data)

def save_csv(path, polys):
    with open(path, "w", encoding="ascii") as f:
        f.write("electrode,x_mm,y_mm\n")
        for number, p in enumerate(polys, 1):
            f.writelines(f"{number},{x:.6f},{y:.6f}\n" for x, y in p)

FORMATS = ["pdf", "svg", "eps", "png", "jpg", "tiff", "dxf", "gbr", "gds", "csv"]
WRITERS = {"dxf": save_dxf, "gbr": save_gerber, "gds": save_gds, "csv": save_csv}

def export(polys, name, formats):
    for ext in formats:
        path = f"{name}.{ext}"
        try:
            if ext in WRITERS:
                WRITERS[ext](path, polys)
            else:
                save_drawing(path, polys, ext)
            print(f"Saved {path}")
        except Exception as error:      # keep going with the other formats
            print(f"Could not save {path}: {error}")

def ask_export(polys):
    print("\nExport formats:")
    for number, ext in enumerate(FORMATS, 1):
        print(f"  {number:>2} = {ext.upper()}")
    print("Type numbers separated by commas (e.g. 1,7), 'all',")
    print("or just press Enter to save nothing.")
    while True:
        text = input("Your choice: ").strip().lower()
        if text == "":
            print("Nothing saved.")
            return
        if text == "all":
            chosen = FORMATS
            break
        items = [t.strip() for t in text.split(",") if t.strip()]
        valid = [str(n) for n in range(1, len(FORMATS) + 1)]
        if items and all(t in valid for t in items):
            chosen = list(dict.fromkeys(FORMATS[int(t) - 1] for t in items))
            break
        print("Please use the numbers from the list.")

    while True:
        name = input("File name [electrode]: ").strip() or "electrode"
        name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        if not name:
            print("Use letters, numbers, spaces, - or _.")
            continue
        if name.upper() in {"CON", "PRN", "AUX", "NUL"}:
            print("Windows reserves that name.")
            continue
        existing = [e for e in chosen if os.path.exists(f"{name}.{e}")]
        if existing and input("Files exist. Overwrite? (y/n): ").lower() != "y":
            continue
        break
    export(polys, name, chosen)

def preview(polys):
    fig, ax = plt.subplots()
    for p, color in zip(polys, ("goldenrod", "steelblue")):
        ax.fill(*zip(*p), color=color, linewidth=0)
    ax.set_aspect("equal")
    ax.set_title("Close this window to continue to export")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    plt.show()

def main():
    pts = ask_points()
    while True:
        width = ask("Finger width (mm)", 0.3)
        gap = ask("Gap (mm)", 0.3)
        busbar = ask("Busbar width (mm)", 0.8)
        height = max(y for _, y in pts) - min(y for _, y in pts)
        try:
            if height / (width + gap) > 2000:
                raise ValueError("That means over 2000 fingers. Use larger sizes.")
            a, b = fill(pts, width, gap, busbar)
            break
        except ValueError as error:
            print(error)
            if input("Try other sizes? (y/n): ").lower() != "y":
                return
    polys = [merge(a, True), merge(b, False)]
    smallest = distance(*polys)
    print(f"{len(a) + len(b) - 2} fingers drawn")
    print(f"Smallest gap between electrodes: {smallest:.3f} mm")
    if smallest < gap - 1e-4:
        print("WARNING: smaller than requested. Do not fabricate this design.")
    preview(polys)
    ask_export(polys)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
