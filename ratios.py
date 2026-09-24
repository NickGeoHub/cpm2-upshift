"""
ratios.py
=========
All known gearbox configurations for the shift calculator, in one place.
Add / edit / remove a car's gear ratios here without touching the main
script at all.

Each entry: short key -> (display name, gear ratios list, 1st gear first).
Pick one with -g/--gearbox on the command line; DEFAULT_GEARBOX below is
used if -g isn't given.
"""

GEARBOXES = {
    "OG_7dsg": ("old config of 7dsg",
                [2.858, 2.263, 1.792, 1.419, 1.123, 0.889, 0.716]),

    "7 DSG DCT/AWD": ("Best AWD",
             [2.858, 2.066, 1.656, 1.364, 1.142, 0.966, 0.815]),

    "7DLC750 V1_speed": ("andrias supercar max speed",
                           [2.769, 1.97, 1.518, 1.197, 0.958, 0.774, 0.63]),

    "7DLC750 V1_drag": ("best RWD tune fr a=0.8, for drag",
                        [2.769, 2.051, 1.63, 1.325, 1.092, 0.909, 0.762]),

    "F1_FMM91": ("F1 gearbox alpha=0.8",
                            [2.835, 2.337, 2.025, 1.781, 1.579, 1.408]),

    "F1_FMM19": ("F1 gearbox a=0.82",
                 [3.5, 2.709, 2.227, 1.863, 1.576, 1.342, 1.15, 0.99]),

    "F1_ZF-hp..ragac": ("F1 4 gear, simple",
                        [2.231, 1.458, 1.064, 0.801]),

    "7 DSG/S DCT/4WD": ("recomended 4WD for drag",
                        [3.323, 2.241, 1.673, 1.286, 1.006, 0.796, 0.636]),

    "klst AWD": ("i am not using it.",
             [4.248, 3.404, 2.728, 2.187, 1.752, 1.404, 1.126, 0.902, 0.723]),

    "7S TRONIC DCT/AWD": ("6 gear AWD",
                          [3.933, 2.64, 1.964, 1.505, 1.174, 0.927])
}


def ask_gearbox(message: str="Pick any gearbox!",
                list_them: bool=True,
                command: str|None = None):
    """
    message - - - -- message which should be displayed at first
    list_them - - -- if it is true, it lists gearboxes
    command - - - -- command can be given as parameter not only as stdin,
                    so gearbox index or list/help commands can be done
                    without stdin.
    """

    # TODO if command is incorrect and try/except handles it, next time input() will ask again. so i dont like it.

    print(message)

    if list_them:
        for i, (name, (description, g_ratios)) in enumerate(GEARBOXES.items()):
            # print(f"i={i}, name={name}, description={description}, gear_ratios={g_ratios}")
            print(f"{str(i).rjust(3)}) {name.ljust(20)}| {description.ljust(45)}| {g_ratios}")

    if command is None:
        ans = input("pick any number: ")
    else:
        ans = str(command)

    # TODO i should add input 00 so it exits or does something useful and needed
    # TODO also add help/?/list keywords so they do their staff
    # if user just clicks enter, ans="", so we may suggest defualt one like that rwd which has low jumps

    try:
        ans = int(ans)
    except ValueError:
        return ask_gearbox("input integer!", list_them=False)

    # now we have integer. woohoo
    try:
        name, (description, g_ratios) = list(GEARBOXES.items())[ans]
    except IndexError:
        return ask_gearbox(f"input number between 0-{len(GEARBOXES)-1}", list_them=False)

    return name, g_ratios


if __name__ == "__main__":
    GN, GEAR_RATIOS = ask_gearbox()
    print(f"GN={GN}, GEAR_RATIOS={GEAR_RATIOS}")
