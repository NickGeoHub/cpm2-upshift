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
# ============================================================  ------------------- GEAR RATIOS ---

# Gear ratios in order, 1st gear first. No final drive needed (see above).


# GN:6L90
GEAR_RATIOS = [3.627, 2.47, 1.683, 1.146, 0.78, 0.737]
# GN:ZF 5H30
GEAR_RATIOS = [3.208, 2.191, 1.497, 1.022, 0.75]

# GN:ZF 8HP90
GEAR_RATIOS = [4.239, 3.129, 2.31, 1.75, 1.325, 1.004, 0.84, 0.737]


# one of the best arrangements for civic
# GEAR_RATIOS = [3.177, 2.443, 1.834, 1.419, 1.163, 0.966, 0.875]
# FD = 2.585

# GN:ZF 4HP22  ===================    popularuli gearboxi (default)
GEAR_RATIOS = [2.48, 1.48, 1, 0.73] 

# GN:ZF 4HP22  ===================    popularuli gearboxi (tuned, minimized drops) === 1.424 drop
GEAR_RATIOS = [2.232, 1.566, 1.1, 0.772] 

# GN:ZF 4HP22  ===================    popularuli gearboxi (tuned, minimized dros + 3->4 1.369)
GEAR_RATIOS = [2.232, 1.566, 1.1, 0.803] 

# GN:6ASG AT RWD / 78 === 1.289 drop (second place, but rwd)
GEAR_RATIOS = [2.908, 2.255, 1.748, 1.356, 1.051, 0.815]

# Civic_b16 ========= Gearbox Name: GSG/A-TRONIC (A/T AWD) / 88KG
GEAR_RATIOS = [3.207, 2.261, 1.570, 1.124, 0.810, 0.582, 0.486]
FD = "max number"

# Dodge charger ===== GN: KLST (A/T AWD) / 75
# GEAR_RATIOS = [4.248, 3.429, 2.947, 2.475, 1.737, 1.25,  1.737, 1.37]
GEAR_RATIOS = [4.248, 3.404, 2.728, 2.187, 1.752, 1.404, 1.126, 0.902, 0.723]  # seems to be best, why i am not using

# GN:ZF 5HP30 AT RWD === 1.4638 drop
GEAR_RATIOS = [3.208, 2.191, 1.497, 1.022, 0.75]

# Dodge charger ===== GN: 7 DSG AT AWD / 92  ===================================== best GEAR RATIOS  === 1.263 drop
GEAR_RATIOS = [2.858, 2.263, 1.792, 1.419, 1.123, 0.889, 0.716]


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

DYNO_RPM, DYNO_TORQUE = dyno_chart_extractor.get_dyno_data(IMAGE_PATH)


# REDLINE_RPM = DYNO_RPM[-1]   # top of the search range
REDLINE_RPM = DYNO_RPM[-2]
MIN_RPM     = 2000   # bottom of the search range (idle / lowest usable RPM)

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
                print(f"{label:<10}{'redline':<14}=(gear {i+1} stays ahead all the way -- shift at redline={REDLINE_RPM})")
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