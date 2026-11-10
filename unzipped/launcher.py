from pathlib import Path
import os
import subprocess
import sys

PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENTS = PROJECT_DIR / "requirements.txt"


def run(command):
    """Run a command and stop if it fails."""
    subprocess.run(command, cwd=PROJECT_DIR, check=True)


def main():
    os.chdir(PROJECT_DIR)

    # Create the virtual environment the first time the launcher runs.
    if not VENV_DIR.exists():
        print("Creating the Python environment...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])

    # Use the virtual environment's Python, not the system Python.
    if os.name == "nt":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"

    if not venv_python.exists():
        raise FileNotFoundError(
            f"Could not find the virtual environment Python at: {venv_python}"
        )

    # Install dependencies the first time. This marker avoids reinstalling
    # everything every time the app is opened.
    install_marker = VENV_DIR / ".requirements_installed"
    if not install_marker.exists():
        print("Installing required packages. This may take a few minutes...")
        run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        install_marker.touch()

    print("Starting the Christmas Lithophane Generator...")
    run([str(venv_python), "-m", "streamlit", "run", "app.py"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApp stopped.")
    except Exception as error:
        print(f"\nLauncher error: {error}")
        input("\nPress Enter to close...")
