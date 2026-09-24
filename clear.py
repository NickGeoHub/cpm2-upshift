from pathlib import Path
import subprocess


def clear_metadata(directory: str="./screenshots") -> None:
    """
    Remove metadata from every file in the specified directory.
    Requires ExifTool to be installed.
    """

    directory = Path(directory)

    if not directory.is_dir():
        raise ValueError(f"Directory does not exist: {directory}")

    for file in directory.iterdir():
        if not file.is_file():
            continue

        print(f"Cleaning: {file.name}")

        result = subprocess.run(
            ["exiftool", "-all=", "-overwrite_original", str(file)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip()}")
        else:
            print("  OK")


if __name__ == "__main__":
    clear_metadata("./screenshots")
