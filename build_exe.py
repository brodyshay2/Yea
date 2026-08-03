"""
Build script — compiles fortnitechecker.py into a standalone Windows .exe
using PyInstaller.

Usage:
    pip install pyinstaller
    python build_exe.py

Output:  dist/FortniteChecker.exe
"""

import subprocess
import sys
import os


def main():
    script = os.path.join(os.path.dirname(__file__), "fortnitechecker.py")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",               # single .exe file
        "--console",               # keep console window (needed for input prompts)
        "--name", "FortniteChecker",
        "--clean",                 # clean build cache first
        script,
    ]

    print("Building FortniteChecker.exe ...")
    print(" ".join(cmd))
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe = os.path.join("dist", "FortniteChecker.exe")
        print(f"\n✅ Build successful! Executable: {exe}")
    else:
        print("\n❌ Build failed. Check the output above for errors.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
