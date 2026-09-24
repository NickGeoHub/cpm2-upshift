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
import ratios
import files


# ============================================================
# YOUR CAR -- edit this section with your CPM2 data
# ============================================================  ------------------- GEAR RATIOS ---

# Gear ratios in order, 1st gear first. No final drive needed (see above).



if __name__ == "__main__":
    # TODO it might be buggy if imported from another file so be carreful
    CROP_BOX = dyno_chart_extractor.CROP_BOX
    SAMPLE_STEP_RPM = dyno_chart_extractor.SAMPLE_STEP_RPM

    parser = argparse.ArgumentParser(description="Calculate best upshift RPMs for each gear, when gear ratios, and dyno data are given")
    parser.add_argument("-f", "--file", default="SCRIPT_ASKS",
                        help="path to the dyno screenshot (default: %(default)s)")
    parser.add_argument("-g", "--gearbox", default="SCRIPT_ASKS",
                        choices=list(ratios.GEARBOXES.keys()),
                        help="which gearbox to use (default: %(default)s)")
    parser.add_argument("--crop", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                        default=list(CROP_BOX),
                        help="pixel box around the chart (default: %(default)s)")
    parser.add_argument("--step", type=int, default=SAMPLE_STEP_RPM,
                        help="RPM step between sampled points (default: %(default)s)")
    args = parser.parse_args()

    CROP_BOX = tuple(args.crop)
    SAMPLE_STEP_RPM = args.step

# should it be in if __name__ == ...... block?
if args.file == "SCRIPT_ASKS":
    # interactive mode
    IMAGE_PATH = files.pick_file_interactively()
else:
    IMAGE_PATH = args.file

if args.gearbox == "SCRIPT_ASKS":
    GN, GEAR_RATIOS = ratios.ask_gearbox()
else:
    GN, GEAR_RATIOS = ratios.GEARBOXES[args.gearbox]



# Dyno run results: RPM vs torque, read straight off your in-game dyno.
# Units don't matter (Nm or lb-ft) as long as they're consistent --
# the math only ever compares torque values to each other.


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

    # added comment here on 168th line
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

    for i in range(len(GEAR_RATIOS)):
        if i == len(GEAR_RATIOS) - 1:
            # we are calculating imaginary gear ratio
            # experiment imaginary gear

            # last gear
            ratio_a = GEAR_RATIOS[i]
            # previous gear ratio jump (n/n+1)
            gear_jump = GEAR_RATIOS[i-1] / GEAR_RATIOS[i]
            # average that jump with 1.0
            ratio_difference = (gear_jump + 1.0) / 2.0
            # imaginary gear
            ratio_b = ratio_a / ratio_difference
            label = f"{i+1} -> #{i+2}#"

        else:
            ratio_a, ratio_b = GEAR_RATIOS[i], GEAR_RATIOS[i + 1]
            ratio_difference = ratio_a/ratio_b
            label = f"{i+1} -> {i+2}"

        crossings, end_diff = find_shift_rpm(ratio_a, ratio_b, MIN_RPM, REDLINE_RPM)

        if not crossings:
            if end_diff > 0:
                print(f"{label:<10}{'redline':<14}=(gear {i+1} stays ahead all the way -- shift at redline={REDLINE_RPM})  ratio_diff={ratio_difference :<14.3f}")
                shift_points.append((REDLINE_RPM, ratio_a))
            else:
                print(f"{label:<10}{MIN_RPM:<14}(gear {i+2} is already ahead from {MIN_RPM} RPM -- shift ASAP)")
                shift_points.append((MIN_RPM, ratio_a))
            continue

        shift_rpm = crossings[-1]
        landing_rpm = shift_rpm * (ratio_b / ratio_a)
        print(f"{label:<10}{shift_rpm:<14.0f}{landing_rpm:<14.0f}{ratio_difference:<14.3f}")
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