
import argparse
import math

parser = argparse.ArgumentParser(description="Calculate best upshift RPMs for each gear, when gear ratios, and dyno data are given")
parser.add_argument("-a", "--alpha", type=bool, default=False,
                     help="should program only calculate alpha? when True -> calculates alpha based on current gear ratios, when False -> generates gear ratios normally (default: %(default)s)")
args = parser.parse_args()

CALC_ALPHA = args.alpha


def generate_ratios(R_max: float,
                    R_min: float,
                    N: int,
                    alpha: float):
    """
    R_max --- first gear ratio
    R_min --- top gear ratio
    N   - --- amount of gears
    alpha
    """

    for n in range(1, N+1):
        R_n = R_max * (R_min/R_max)**(((n-1)/(N-1))**alpha)
        yield round(R_n, 3)


def print_gears(ratios):
    print(f"{'gear#':<7}{'ratio':<10}{'n/n+1':<10}")
    print("-" * 22, "=" * 10, sep='')

    for i in range(len(ratios)):
        try:
            ratio_drop = ratios[i]/ratios[i+1]
        except IndexError:
            ratio_drop = 0
        print(f"{i+1:<7}{ratios[i]:<10.3f}{ratio_drop:<10.3f}{1.1:<14.3f}")

    print()
    print(f"GEAR_RATIOS = {ratios}")


if __name__ == "__main__":
    if CALC_ALPHA:
        N = int(input("how much gears it got? "))
        R_max = float(input(f"what is gear#1 ratio? "))
        R_min = float(input(f"what is gear#{N} raito? "))
        n = int(input(f"choose number between 1-{N}: "))
        R_n = float(input(f"what is gear#{n} raito? "))

        alpha = math.log((math.log((R_n/R_max), (R_max/R_min))), ((n-1)/(N-1)))

    # STARTS HERE /.,mnbvcvbnm,./.,mnbvcvbnm,./.,mnbvcvbnm,./.,mnbvvbnm,./
    R_max = 2.769
    R_min = 0.63
    N = 7

    # recomended to be between 0.7 and 0.9
    # i liked 0.75 on dodge.
    # 0.9 setting --> each lands slightly lower rmp
    # 0.6 setting --> first lands far low rpm, then idk why but i get almost consistent lands...
    # i think 0.8 should be best setting.

    alpha = 0.82

    GEAR_RATIOS = [i for i in generate_ratios(R_max=R_max, R_min=R_min, N=N, alpha=alpha)]
    print_gears(GEAR_RATIOS)
