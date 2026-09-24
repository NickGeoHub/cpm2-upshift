import os

def pick_file_interactively(message: str="Pick dyno file!",
                            list_them: bool=True,
                            command: str|None = None,
                            search_dir="./screenshots",
                            extensions=(".jpg", ".jpeg", ".png")):
    """
    Lists image files found in search_dir, numbered, and lets you pick
    by typing either the number or the filename itself. Used when
    -f/--file wasn't given on the command line.
    """
    # TODO add docstrings & implement command list/help...
    print(message)
    files = sorted(f for f in os.listdir(search_dir) if f.lower().endswith(extensions))
    if not files:
        raise SystemExit(f"No image files found in '{search_dir}'.")
    print(f"No -f given -- found {len(files)} screenshot(s) in '{search_dir}':")
    if list_them:
        for i, f in enumerate(files, start=1):
            print(f"{str(i).rjust(3)}) {f}")
    choice = input("Pick a number or type a filename: ").strip()

    # filename matched exactly
    if choice in files:
        return os.path.join(search_dir, choice)

    # user typed filename without extension
    for ext in extensions:
        if choice+ext in files:
            return os.path.join(search_dir, choice+ext)

    # user picked num
    if choice.isdigit():
        if 1 <= int(choice) <= len(files):
            return os.path.join(search_dir, files[int(choice) - 1])
        else:
            return pick_file_interactively(f"Pick number between 1-{len(files)} or type filename!",
                                    list_them=False)
    else:
        # use correct file name or pick a number.
        return pick_file_interactively(f"your input is not number. pick number or write correct file name.")


if __name__ == "__main__":
    print(f"returned: {pick_file_interactively()}")