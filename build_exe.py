"""
Build script to package the Image to PDF Converter into a standalone Windows .exe
"""

import os
import sys
import subprocess
import shutil

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "icon.ico")
    main_script = os.path.join(base_dir, "main.py")

    print("=== Building ImageToPDFConverter Standalone Executable ===")
    
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "ImageToPDFConverter",
    ]

    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
        cmd.extend(["--add-data", f"{icon_path};."])

    cmd.append(main_script)

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=base_dir)

    if res.returncode == 0:
        exe_path = os.path.join(base_dir, "dist", "ImageToPDFConverter.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print("\n=======================================================")
            print(f"SUCCESS! Executable created successfully:")
            print(f"Path: {exe_path}")
            print(f"Size: {size_mb:.2f} MB")
            print("=======================================================\n")
            return True
    
    print("\nBUILD FAILED with return code:", res.returncode)
    return False

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
