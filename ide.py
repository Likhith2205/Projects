import math
import matplotlib.pyplot as plt

def is_convex(pts):
    """True if the outline never turns inwards or crosses itself."""
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
    print("Enter the corners in order as x,y in mm (example: 10,0).")
    print("Press Enter on an empty line when finished.")
    pts = []
    while True:
        text = input(f"Corner {len(pts) + 1}: ").strip()
        if text == "":
            if len(pts) >= 3 and is_convex(pts):
                return pts
            print("Need 3+ corners with no inward dents. Start again.")
            pts = []
            continue
        try:
            x, y = text.split(",")
            pts.append((float(x), float(y)))
        except ValueError:
            print("Type two numbers with a comma, e.g. 2.5,4")

def ask(prompt, default):
    while True:
        text = input(f"{prompt} [{default}]: ").strip()
        try:
            value = float(text) if text else default
            if value > 0:
                return value
        except ValueError:
            pass
        print("Please enter a positive number.")

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

def fill(pts, width, gap, busbar):
    low = min(y for _, y in pts)
    high = max(y for _, y in pts)
    L = lambda y: edges_at(pts, y)[0]
    R = lambda y: edges_at(pts, y)[1]

    # use only heights wide enough for two busbars and a gap
    samples = [low + (high - low) * k / 2000 for k in range(2001)]
    usable = [y for y in samples if R(y) - L(y) >= 2 * busbar + 2 * gap]
    if not usable:
        raise SystemExit("Outline is too narrow. Reduce busbar or gap.")
    y0, y1 = usable[0], usable[-1]
    ys = levels(pts, y0, y1)

    a = [band(ys, L, lambda y: L(y) + busbar)]     # left electrode
    b = [band(ys, lambda y: R(y) - busbar, R)]     # right electrode

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
        if i % 2 == 0:
            start, end = (lambda t: L(t) + busbar), (lambda t: other(t) - clear)
        else:
            start, end = (lambda t: other(t) + clear), (lambda t: R(t) - busbar)
        if all(end(t) > start(t) for t in fy):
            (a if i % 2 == 0 else b).append(band(fy, start, end))
        y += width + gap
        i += 1
    return a, b

def main():
    pts = ask_points()
    width = ask("Finger width (mm)", 0.3)
    gap = ask("Gap (mm)", 0.3)
    busbar = ask("Busbar width (mm)", 0.8)
    a, b = fill(pts, width, gap, busbar)
    print(f"{len(a) - 1 + len(b) - 1} fingers drawn")

    fig, ax = plt.subplots()
    for electrode, color in ((a, "goldenrod"), (b, "steelblue")):
        for poly in electrode:
            ax.fill(*zip(*poly), color=color, linewidth=0)
    ax.plot(*zip(*(pts + pts[:1])), "k--", linewidth=0.5)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    plt.show()

if __name__ == "__main__":
    main()