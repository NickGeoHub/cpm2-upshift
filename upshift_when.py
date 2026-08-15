#!/usr/bin/env python3
"""
CPM2 Shift Point Calculator
============================
Finds the exact RPM to upshift each gear at, for maximum acceleration.

THE MATH
--------
What accelerates the car is torque delivered to the wheels -- not raw
engine torque, and not horsepower. In a given gear:

    wheel_torque(RPM) = engine_torque(RPM) * gear_ratio

(Final drive ratio and tire radius also multiply this in real life, but
they're the same in every gear, so they cancel out when comparing gears
against each other. They only matter if you want actual road speed, not
RPM -- which is why they're not inputs here.)

When you upshift from gear A to gear B, engine RPM drops in proportion
to the ratio change, since road speed doesn't change instantly:

    RPM_B = RPM_A * (ratio_B / ratio_A)

The optimal shift point is the RPM_A where staying in gear A stops
beating gear B -- i.e. where wheel torque is equal in both:

    engine_torque(RPM_A) * ratio_A  ==  engine_torque(RPM_B) * ratio_B

Below that RPM, gear A puts more torque down. Above it, gear B does.
This is the "crossover point" -- shift exactly there and you're always
making the most torque possible at your current speed, gear after gear.

Horsepower is not needed as an input: HP = torque * RPM * constant, so
it carries no information the torque curve doesn't already have.

Only dependency: numpy (pip install numpy).
"""

import argparse
import numpy as np
# import matplotlib.pyplot as plt

import dyno_chart_extractor


# ============================================================
# YOUR CAR -- edit this section with your CPM2 data
# ============================================================

# Gear ratios in order, 1st gear first. No final drive needed (see above).
GEAR_RATIOS = [3.176, 2.245, 1.644, 1.265, 1.025, 0.851, 0.77]

GEAR_RATIOS = [4.37, 2.7, 1.92, 1.5, 1.23, 0.97]
GEAR_RATIOS = [4.340, 2.650, 1.910, 1.500, 1.230, 1.025]
GEAR_RATIOS = [2.740, 2.740, 1.920, 1.500, 1.190, 0.952]
del GEAR_RATIOS
GEAR_RATIOS = [3.933, 2.619, 1.940, 1.492, 1.148, 0.927]
GEAR_RATIOS = [0.8 * (1.07**i) for i in range(20)]
GEAR_RATIOS.reverse()


IMAGE_PATH = dyno_chart_extractor.IMAGE_PATH
CROP_BOX = dyno_chart_extractor.CROP_BOX
SAMPLE_STEP_RPM = dyno_chart_extractor.SAMPLE_STEP_RPM


parser = argparse.ArgumentParser(description="Calculate best upshift RPMs for each gear, when gear ratios, and dyno data are given")
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



# Dyno run results: RPM vs torque, read straight off your in-game dyno.
# Units don't matter (Nm or lb-ft) as long as they're consistent --
# the math only ever compares torque values to each other.

# that is for my napovni manqana
# DYNO_RPM = [700,    800,   900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900, 4000, 4100, 4200, 4300, 4400, 4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400, 5500, 5600, 5700, 5800, 5900, 6000, 6100, 6200, 6300, 6400, 6500, 6600, 6700, 6800, 6900, 7000]
# DYNO_TORQUE = [954, 1011, 1098, 1178, 1247, 1313, 1379, 1439, 1488, 1526, 1564, 1594, 1621, 1638, 1657, 1672, 1681, 1691, 1702, 1715, 1725, 1740, 1749, 1764, 1777, 1793, 1803, 1815, 1824, 1832, 1834, 1834, 1836, 1836, 1841, 1846, 1851, 1856, 1852, 1845, 1839, 1832, 1822, 1810, 1790, 1760, 1750, 1740, 1730, 1720, 1700, 1670, 1635, 1600, 1550, 1395, 1342, 1276, 1247, 1231, 1195, 1162, 1129, 1102]

# cls
DYNO_RPM = [600,  700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900, 4000, 4100, 4200, 4300, 4400, 4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400, 5500, 5600, 5700, 5800, 5900, 6000, 6100, 6200, 6300, 6400, 6500, 6600, 6700, 6800, 6900, 7000]
DYNO_TORQUE = [334, 357, 386, 421, 457, 498, 542,   590, 637, 684, 721,    746, 766,   787, 801,   806, 809, 810,    810, 810, 811,    812, 812, 813,    814, 814, 815,    815, 815, 816,    817, 817, 818,    819, 820, 821,    821, 822, 821,    820, 817, 809,    800, 792, 780,    759, 709, 699,    685, 674, 662,    652, 641, 632,    626, 621, 588, 564, 537, 533, 531, 521, 511, 502, 493]

# jetta like
DYNO_RPM = [800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900, 4000, 4100, 4200, 4300, 4400, 4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400, 5500, 5600, 5700, 5800, 5900, 6000, 6100, 6200, 6300, 6400, 6500, 6600, 6700, 6800, 6900, 7000, 7100, 7200, 7300, 7400]
DYNO_TORQUE = [202, 213, 228, 249, 274, 300, 326, 345, 354, 357, 358, 360, 361, 362, 364, 365, 364, 363, 362, 362, 361, 362, 361, 362, 362, 362, 362, 362, 362, 362, 362, 362, 361, 361, 361, 360, 360, 358, 355, 351, 346, 341, 336, 330, 325, 319, 313, 307, 302, 297, 291, 287, 282, 277, 273, 269, 263, 256, 247, 234, 221, 207, 188, 166, 155, 144, 132]

DYNO_RPM, DYNO_TORQUE = dyno_chart_extractor.get_dyno_data(IMAGE_PATH)


# REDLINE_RPM = DYNO_RPM[-1]   # top of the search range
REDLINE_RPM = 6000
MIN_RPM     = 5000   # bottom of the search range (idle / lowest usable RPM)

SHOW_PLOT = True
# SHOW_PLOT = False    # set True to save a wheel-torque-vs-speed chart (needs matplotlib)

# ============================================================
# CALCULATION -- shouldn't need to touch this
# ============================================================

def engine_torque(rpm):
    """Torque at a given RPM, interpolated from the dyno data."""
    return np.interp(rpm, DYNO_RPM, DYNO_TORQUE)


def wheel_torque(rpm, ratio):
    """Torque to the wheels at this RPM/gear (up to a constant factor)."""
    return engine_torque(rpm) * ratio


def find_shift_rpm(ratio_a, ratio_b, lo, hi, steps=4000):
    """
    Scan [lo, hi] for RPM(s) in gear A where wheel torque in gear A
    equals wheel torque in gear B at the matching road speed.
    Returns (list_of_crossover_rpms, sign_at_hi).
    """
    def diff(rpm_a):
        rpm_b = rpm_a * (ratio_b / ratio_a)
        return wheel_torque(rpm_a, ratio_a) - wheel_torque(rpm_b, ratio_b)

    scan = np.linspace(lo, hi, steps)
    vals = [diff(r) for r in scan]

    crossings = []
    eps =1e-9
    for i in range(len(scan) - 1):
        v0, v1 = vals[i], vals[i + 1]
        if abs(v0) < eps:
            crossings.append(scan[i])
        elif v0 * v1 < 0:
            r0, r1 = scan[i], scan[i + 1]
            crossings.append(r0 + (r1 - r0) * (-v0) / (v1 - v0))

    # return crossings, vals[-1]
    return crossings, float(np.sign(vals[-1]))  # if it does not work, uncomment prev line



def plot_wheel_torque_curves(shift_points):
    """
    Plot wheel torque vs a shared road-speed proxy (RPM / gear ratio) so
    curves from different gears line up honestly -- plotting them against
    raw engine RPM instead would make every gear look uniformly "better",
    since it ignores that each gear reaches a given speed at a different RPM.
    """
    import matplotlib.pyplot as plt

    speed_lo = MIN_RPM / GEAR_RATIOS[0]
    speed_hi = REDLINE_RPM / GEAR_RATIOS[-1]
    speed_proxy = np.linspace(speed_lo, speed_hi, 800)

    plt.figure(figsize=(9, 6))
    for i, ratio in enumerate(GEAR_RATIOS):
        rpm_vals = speed_proxy * ratio
        torque_vals = np.where(
            (rpm_vals >= MIN_RPM) & (rpm_vals <= REDLINE_RPM),
            wheel_torque(rpm_vals, ratio),
            np.nan,
        )
        plt.plot(speed_proxy, torque_vals, label=f"Gear {i+1}= {GEAR_RATIOS[i]}")

    for shift_rpm, ratio in shift_points:
        plt.axvline(shift_rpm / ratio, color="gray", linestyle="--", linewidth=0.8)

    plt.xlabel("Road speed (proportional units -- RPM / gear ratio)")
    plt.ylabel("Wheel torque (relative)")
    plt.title("Wheel torque per gear vs road speed -- dashed lines mark each shift point")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("shift_curves.png", dpi=150)
    print("Saved shift_curves.png")


def main():
    print(f"{'Shift':<10}{'Shift @ RPM':<14}{'Lands @ RPM':<14}")
    print("-" * 38)

    shift_points = []  # (shift_rpm, ratio_a) pairs, for the optional plot

    for i in range(len(GEAR_RATIOS) - 1):
        ratio_a, ratio_b = GEAR_RATIOS[i], GEAR_RATIOS[i + 1]
        crossings, end_diff = find_shift_rpm(ratio_a, ratio_b, MIN_RPM, REDLINE_RPM)
        label = f"{i+1} -> {i+2}"

        if not crossings:
            if end_diff > 0:
                print(f"{label:<10}{'redline':<14}(gear {i+1} stays ahead all the way -- shift at redline)")
                shift_points.append((REDLINE_RPM, ratio_a))
            else:
                print(f"{label:<10}{MIN_RPM:<14}(gear {i+2} is already ahead from {MIN_RPM} RPM -- shift ASAP)")
                shift_points.append((MIN_RPM, ratio_a))
            continue

        shift_rpm = crossings[-1]
        landing_rpm = shift_rpm * (ratio_b / ratio_a)
        rato_difference = ratio_a/ratio_b
        print(f"{label:<10}{shift_rpm:<14.0f}{landing_rpm:<14.0f}{rato_difference:<14.3f}")
        shift_points.append((shift_rpm, ratio_a))

        if len(crossings) > 1:
            others = ", ".join(f"{c:.0f}" for c in crossings)
            print(f"    note: {len(crossings)} crossover points found ({others}) -- "
                  f"unusual torque curve, worth checking SHOW_PLOT=True")

    if SHOW_PLOT:
        plot_wheel_torque_curves(shift_points)
        import dyno_chart_extractor
        dyno_chart_extractor.plot_torque_curve(DYNO_RPM, DYNO_TORQUE)


if __name__ == "__main__":
    main()