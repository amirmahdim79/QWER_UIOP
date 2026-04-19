# Build script for QWERC
# Run: python build.py

import subprocess
import shutil
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(ROOT, "build_output")

SOURCES = [
    "config.py",
    "state.py",
    "chords.py",
    "input_handler.py",
    "predictor.py",
    "autocorrect.py",
    "floating_ui.py",
]

def clean():
    for d in ["build", "dist", "build_output"]:
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    spec = os.path.join(ROOT, "QWERC.spec")
    if os.path.isfile(spec):
        os.remove(spec)

def build():
    clean()
    os.makedirs(BUILD_DIR, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--uac-admin",
        "--name", "QWERC",
        "--noconsole",
        "--distpath", BUILD_DIR,
        "--workpath", os.path.join(BUILD_DIR, "_build"),
        "--specpath", BUILD_DIR,
    ]

    for src in SOURCES:
        cmd += ["--add-data", f"{os.path.join(ROOT, src)};."]

    cmd += ["--hidden-import", "tkinter"]
    cmd.append("main.py")

    print("Building QWERC.exe ...")
    result = subprocess.run(cmd, cwd=ROOT)

    # Clean up intermediate files
    work = os.path.join(BUILD_DIR, "_build")
    if os.path.isdir(work):
        shutil.rmtree(work)
    spec = os.path.join(BUILD_DIR, "QWERC.spec")
    if os.path.isfile(spec):
        os.remove(spec)

    exe = os.path.join(BUILD_DIR, "QWERC.exe")
    if result.returncode == 0 and os.path.isfile(exe):
        print(f"\nDone! Executable: {exe}")
    else:
        print("\nBuild failed.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build()
