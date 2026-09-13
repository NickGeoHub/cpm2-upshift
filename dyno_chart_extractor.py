#!/usr/bin/env python3
"""
CPM2 Dyno Chart Extractor
==========================
Reads a screenshot of CPM2's in-game dyno graph and pulls out the torque
and power curves as RPM/value data points -- ready to paste into
cpm2_shift_calculator.py's DYNO_RPM / DYNO_TORQUE variables.

HOW IT WORKS
------------
1. GRIDLINES -> PIXEL COORDINATES OF KNOWN VALUES
   The x-axis RPM labels (0, 1000, 2000, ...) and y-axis value labels
   (0, 90, 180, ...) each have a gridline running the full width/height
   of the plot. A pixel column that's "gridline gray" almost all the
   way down is a vertical gridline; the same check sideways finds
   horizontal gridlines. This tells us e.g. "RPM 5000 sits at pixel
   x=707" for several known values.

2. PIXEL <-> DATA CALIBRATION
   Gridlines are evenly spaced by construction, so fitting a straight
   line (pixel = a*value + b) through the known points via linear
   regression gives a precise, sub-pixel-accurate conversion both ways.

3. TRACE THE CURVES BY COLOR
   Every pixel is checked against the torque curve's color (yellow:
   green and blue channels close together) and the power curve's color
   (red: red channel far above green/blue). For each pixel column that
   has matching pixels, the average position is that curve's height at
   that column -- this "collapses" the curve's line thickness to a
   single centerline value per column.

4. CONVERT BACK TO DATA AND SAMPLE
   Run the traced pixel curve back through the calibration from step 2,
   and read it off at whatever RPM step you want.

CONFIDENCE CHECK
-----------------
Torque (Nm) and power (PS) aren't independent: PS = Nm * RPM / 7127,
always, by definition. This script computes that ratio from the two
traced curves -- if it comes out close to 7127 across the whole range,
that's strong independent confirmation the extraction (and which curve
is which) is actually correct, not just plausible-looking. It'll warn
you if the ratio doesn't hold.

WHAT TO CHECK IF A NEW SCREENSHOT DOESN'T WORK
------------------------------------------------
This relies on CPM2's dyno chart looking the same way each time (same
gridline style, same two curve colors). If a screenshot is a different
resolution or crop, you'll mainly need to adjust CROP_BOX and possibly
the two DETECT bands below. The script saves a debug image after every
run -- ALWAYS eyeball it before trusting the printed numbers.

KNOWN ROUGH SPOTS (check the debug overlay for these, fix by hand if needed)
------------------------------------------------------------------------------
- Wherever the yellow and red lines visually touch/cross, color detection
  can get confused for a handful of RPM and briefly jump off the real
  curve -- this happened around the crossing point on this chart.
- The last stretch before redline, where the curve drops almost straight
  down, is unreliable the same way -- easiest to just eyeball those last
  few hundred RPM off the chart directly rather than trust this script there.
- Either shows up as a value that doesn't fit the smooth trend of its
  neighbors -- compare the printed list against the debug overlay image
  and nudge any obvious outliers by hand.
"""

import argparse
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import os
import subprocess
import sys
from pathlib import Path

# ============================================================
# EDIT THESE per screenshot
# ============================================================



IMAGE_PATH = "screenshots/b16.jpg"

# Pixel box (left, top, right, bottom), in the ORIGINAL screenshot, that
# crops down to just the axes + plot area -- cut out the RPM readout,
# buttons, and background. Open the screenshot in any viewer/editor to
# read off rough pixel coordinates; it doesn't need to be exact, it just
# needs to fully contain the grid with a little margin.
CROP_BOX = (360, 300, 1700, 900)

# The RPM values the x-axis gridlines show, left to right.
# RPM_GRIDLINE_VALUES = [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]
# RPM_GRIDLINE_VALUES = [i for i in range(0, 11000+1, 1000)]

# The values the y-axis gridlines show, top to bottom.
# VALUE_GRIDLINE_VALUES = [i for i in range(900,-1,-100)]

# Curve-free pixel bands (relative to the CROPPED image) used to detect
# gridlines without curve interference. X band = a row range near the
# TOP of the plot, above where either curve ever reaches. Y band = a
# column range near the LEFT edge, before either curve starts. If the
# gridline count warning fires, look at the saved debug image and move
# these to a spot the curves don't touch in your screenshot.

#                        top, bottom
X_GRIDLINE_DETECT_ROWS = (70, 80)

#                        left, right
Y_GRIDLINE_DETECT_COLS = (110, 140)

SAMPLE_STEP_RPM = 100     # how finely to sample the traced curves
MAX_GAP_PX = 10           # a bigger gap than this = stop trusting that curve past it



parser = argparse.ArgumentParser(description="Extract RPM/torque/power data from a CPM2 dyno chart screenshot.")
parser.add_argument("-f", "--file", default=IMAGE_PATH,
                     help="path to the dyno screenshot (default: %(default)s)")
parser.add_argument("--crop", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                     default=list(CROP_BOX),
                     help="pixel box around the chart (default: %(default)s)")
parser.add_argument("--step", type=int, default=SAMPLE_STEP_RPM,
                     help="RPM step between sampled points (default: %(default)s)")
args = parser.parse_args()


IMAGE_PATH = args.file
CROP_BOX = tuple(args.crop)
SAMPLE_STEP_RPM = args.step


# ============================================================
# shouldn't need to touch below here
# ============================================================

def open_file_cross_platform(path: Path):
    path = str(path.resolve())

    # Suppress any stdout/stderr the opener might emit
    DEVNULL = subprocess.DEVNULL

    if sys.platform.startswith("win"):
        # start is a shell built-in; use cmd /c start
        # "" = window title placeholder
        subprocess.Popen(["cmd", "/c", "start", "", path],
                         stdout=DEVNULL, stderr=DEVNULL)

    elif sys.platform == "darwin":
        subprocess.Popen(["open", path],
                         stdout=DEVNULL, stderr=DEVNULL)

    else:
        subprocess.Popen(["xdg-open", path],
                         stdout=DEVNULL, stderr=DEVNULL)


def is_gridline_gray(r, g, b):
    return abs(r - g) < 20 and abs(g - b) < 20 and 100 < r < 230

def is_yellow(r, g, b):   # torque curve
    return r > 140 and (r - g) < 45 and (g - b) > 30

def is_red(r, g, b):      # power curve
    return r > 140 and (r - g) > 55


def find_gridlines(arr, axis, band, expected_values):
    """axis='x': detect vertical gridlines -> pixel column per RPM value.
    axis='y': detect horizontal gridlines -> pixel row per data value.
    `band` is the curve-free pixel range on the OTHER axis to scan."""
    h, w, _ = arr.shape
    lo, hi = band
    if axis == 'x':
        counts = np.array([sum(1 for y in range(lo, hi) if is_gridline_gray(*arr[y, x]))
                            for x in range(w)])
    else:
        counts = np.array([sum(1 for x in range(lo, hi) if is_gridline_gray(*arr[y, x]))
                            for y in range(h)])

    threshold = int((hi - lo) * 0.8)
    hits = np.where(counts > threshold)[0]
    if len(hits) == 0:
        raise RuntimeError(f"No {axis}-axis gridlines detected at all -- CROP_BOX or the "
                            f"detect band is probably wrong. Check debug_crop.png.")

    clusters, cur = [], [hits[0]]
    for v in hits[1:]:
        if v - cur[-1] <= 4:
            cur.append(v)
        else:
            clusters.append(sum(cur) / len(cur))
            cur = [v]
    clusters.append(sum(cur) / len(cur))



    if len(clusters) != len(expected_values):
        print("clusters:", clusters)
        print("cluster count:", len(clusters))
        print("expected count:", len(expected_values))
        raise RuntimeError(
            f"Found {len(clusters)} {axis}-axis gridlines but expected {len(expected_values)} "
            f"(from {'RPM' if axis == 'x' else 'VALUE'}_GRIDLINE_VALUES). Check debug_crop.png "
            f"-- likely CROP_BOX is off, or a curve is crossing through the detect band "
            f"({'X_GRIDLINE_DETECT_ROWS' if axis == 'x' else 'Y_GRIDLINE_DETECT_COLS'})."
        )
    return clusters



def plot_torque_curve(dyno_rpm, dyno_torque, out_path="torque_curve.png"):
    plt.figure(figsize=(9, 6))
    plt.plot(dyno_rpm, dyno_torque, marker='o', markersize=2, color='#e6c34a')
    plt.xticks(RPM_GRIDLINE_VALUES)
    plt.yticks(sorted(VALUE_GRIDLINE_VALUES))
    plt.xlim(min(RPM_GRIDLINE_VALUES), max(RPM_GRIDLINE_VALUES))
    plt.ylim(min(VALUE_GRIDLINE_VALUES), max(VALUE_GRIDLINE_VALUES))
    plt.xlabel("RPM")
    plt.ylabel("Torque")
    plt.title("Torque vs RPM")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    return out_path


def trace_curve_backup(arr, classify_fn):
    """For every pixel column, average the y-position of matching pixels.
    Returns {x: y} for columns where that color was found at all."""
    h, w, _ = arr.shape
    curve = {}
    for x in range(w):
        ys = [y for y in range(h) if classify_fn(*arr[y, x])]
        if ys:
            curve[x] = sum(ys) / len(ys)
    return curve

def trace_curve(arr, classifier, max_jump=30):
    """
    Same as before, but only trusts matches within `max_jump` pixels of
    the previous column's position. This throws out far-away false
    positives (background glare, a gridline crossing, etc.) instead of
    averaging them into the centroid and dragging the trace off-line.
    Bump max_jump if a genuinely steep part of the curve gets skipped;
    lower it if bad matches still get through.
    """
    h, w, _ = arr.shape
    points = {}
    prev_y = None
    for x in range(w):
        col = arr[:, x, :]
        ys = [y for y in range(h) if classifier(*col[y])]
        if prev_y is not None:
            ys = [y for y in ys if abs(y - prev_y) <= max_jump]
        if not ys:
            continue
        y = sum(ys) / len(ys)
        points[x] = y
        prev_y = y
    return points


def fill_hidden_gaps(curve_points, other_curve_points, max_gap=30):
    """
    Fills gaps in curve_points using other_curve_points' value at the
    same x -- for the case where the yellow (torque) line gets covered
    by the red (power) line where they cross, so yellow's real pixels
    just aren't there to read. Assumes yellow sits right under red at
    that spot, which is the best guess available when it's hidden.

    Only fills gaps up to max_gap pixels wide, so it doesn't wrongly
    borrow red's data across a big, unrelated gap (like the near-redline
    dropout) -- that should stay a real gap, not get papered over.
    """
    if not curve_points:
        return curve_points
    xs = sorted(curve_points)
    filled = dict(curve_points)
    for i in range(len(xs) - 1):
        gap = xs[i + 1] - xs[i]
        if 1 < gap <= max_gap:
            for x in range(xs[i] + 1, xs[i + 1]):
                if x in other_curve_points:
                    filled[x] = other_curve_points[x]
    return filled


def reliable_range(curve, max_gap):
    """Returns (first_x, last_x_before_first_big_gap). A screenshot's
    curve sometimes has a short break (colors overlapping at a crossing
    point, or heavy compression near a steep drop) -- rather than
    silently interpolating across a long blind spot, stop at the last
    point before any gap bigger than max_gap."""
    xs = sorted(curve)
    for i in range(len(xs) - 1):
        if xs[i + 1] - xs[i] > max_gap:
            print(f"  note: {max_gap}+ px gap in this curve at x={xs[i]}-{xs[i+1]} "
                  f"-- trusting data only up to x={xs[i]}")
            return xs[0], xs[i]
    return xs[0], xs[-1]


def get_dyno_data(image_path: str,
                  crop_box: tuple[int] = CROP_BOX):
    full_img = Image.open(image_path).convert("RGB")
    img = full_img.crop(crop_box)
    crop_path = Path("debug_crop.png")
    img.save(crop_path.resolve())
    arr = np.array(img).astype(int)

    open_file_cross_platform(crop_path)
    global RPM_GRIDLINE_VALUES, VALUE_GRIDLINE_VALUES
    RPM_GRIDLINE_VALUES = [i for i in range(0, int(input("what is Max value of RPM Axis? "))+1, 1000)]
    VALUE_GRIDLINE_VALUES = [i for i in range(int(input("what is Max value of Torque Axis? ")),-1,-int(input("what is Min value of Torque Axis? ")))]
    print(RPM_GRIDLINE_VALUES)
    print(VALUE_GRIDLINE_VALUES)

    x_px = find_gridlines(arr, 'x', X_GRIDLINE_DETECT_ROWS, RPM_GRIDLINE_VALUES)
    y_px = find_gridlines(arr, 'y', Y_GRIDLINE_DETECT_COLS, VALUE_GRIDLINE_VALUES)
    mx, cx = np.polyfit(RPM_GRIDLINE_VALUES, x_px, 1)
    my, cy = np.polyfit(VALUE_GRIDLINE_VALUES, y_px, 1)

    def rpm_to_px(rpm):
        return mx * rpm + cx

    def px_to_rpm(px):
        return (px - cx) / mx

    def px_to_val(px):
        return (px - cy) / my

    print("Tracing torque curve (yellow)...")
    yellow = trace_curve(arr, is_yellow)
    print("Tracing power curve (red)...")
    red = trace_curve(arr, is_red)

    # EXPERIMENTAL
    yellow = fill_hidden_gaps(yellow, red)


    # debug overlay: gridlines + traced curves, so you can eyeball correctness
    overlay = img.copy()
    draw = ImageDraw.Draw(overlay)


    h, w, _ = arr.shape

    # X gridline detector: checks this horizontal strip
    x_lo, x_hi = X_GRIDLINE_DETECT_ROWS
    draw.rectangle(
        [(0, x_lo), (w - 1, x_hi - 1)],
        outline=(255, 255, 0),
        width=3,
    )

    # Y gridline detector: checks this vertical strip
    y_lo, y_hi = Y_GRIDLINE_DETECT_COLS
    draw.rectangle(
        [(y_lo, 0), (y_hi - 1, h - 1)],
        outline=(255, 0, 255),
        width=3,
    )












    for px in x_px:
        draw.line([(px, 0), (px, overlay.height)], fill=(0, 200, 255), width=1)
    for px in y_px:
        draw.line([(0, px), (overlay.width, px)], fill=(0, 200, 255), width=1)
    for x, y in yellow.items():
        draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(0, 255, 0))
    for x, y in red.items():
        draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 0, 255))
    overlay.save("debug_trace_overlay.png")

    y_lo, y_hi = reliable_range(yellow, MAX_GAP_PX)
    r_lo, r_hi = reliable_range(red, MAX_GAP_PX)
    rpm_lo = max(px_to_rpm(y_lo), px_to_rpm(r_lo))
    rpm_hi = min(px_to_rpm(y_hi), px_to_rpm(r_hi))

    start = int(np.ceil(rpm_lo / SAMPLE_STEP_RPM)) * SAMPLE_STEP_RPM
    end = int(np.floor(rpm_hi / SAMPLE_STEP_RPM)) * SAMPLE_STEP_RPM
    rpms = list(range(start, end + 1, SAMPLE_STEP_RPM))

    yx = np.array(sorted(yellow)); yy = np.array([yellow[x] for x in yx])
    rx = np.array(sorted(red)); ry = np.array([red[x] for x in rx])

    def sample(rpm, cxa, cya):
        return px_to_val(np.interp(rpm_to_px(rpm), cxa, cya))

    torque = [round(sample(r, yx, yy)) for r in rpms]
    power = [round(sample(r, rx, ry)) for r in rpms]

    ratios = [p / (t * r) for r, t, p in zip(rpms, torque, power) if t > 20]
    implied_constant = 1 / (sum(ratios) / len(ratios))
    print(f"\nSanity check: implied torque/power constant = {implied_constant:.0f} "
          f"(~7127 confirms yellow=torque Nm / red=power PS; ~5252 would mean "
          f"lb-ft/HP instead -- if it's neither, something's misdetected)")

    print(f"\nSaved debug_crop.png and debug_trace_overlay.png -- check them before trusting this:\n")

    print(f"HP = {power}")

    plot_torque_curve(rpms, torque)

    # TODO change those value format from 2x lists to 1 dictionary
    # for i in range(len(rpms)):
    #     print(f"rpm:tq = {rpms[i]}:{torque[i]}")
    return rpms, torque


def plot_torque_curve(dyno_rpm, dyno_torque, out_path="torque_curve.png"):
    plt.figure(figsize=(9, 6))
    plt.plot(dyno_rpm, dyno_torque, marker='o', markersize=2, color='#e6c34a')
    plt.xticks(RPM_GRIDLINE_VALUES)
    plt.yticks(sorted(VALUE_GRIDLINE_VALUES))
    plt.xlim(min(RPM_GRIDLINE_VALUES), max(RPM_GRIDLINE_VALUES))
    plt.ylim(min(VALUE_GRIDLINE_VALUES), max(VALUE_GRIDLINE_VALUES))
    plt.xlabel("RPM")
    plt.ylabel("Torque")
    plt.title("Torque vs RPM")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    return out_path


if __name__ == "__main__":
    rpms, torque = get_dyno_data(IMAGE_PATH)
    print("DYNO_RPM =", rpms)
    print("DYNO_TORQUE =", torque)
