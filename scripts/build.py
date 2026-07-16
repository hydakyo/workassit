import subprocess
import sys
from pathlib import Path

def main():
    print("Building Project OS using PyInstaller...")
    
    root_dir = Path(__file__).parent.parent
    main_script = root_dir / "main.py"
    
    if not main_script.exists():
        print(f"Error: Could not find main.py at {main_script}")
        sys.exit(1)
        
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "ProjectOS",
        "--clean",
        str(main_script)
    ]
    
    # CustomTkinter needs some extra data files sometimes, but let's try basic first
    try:
        subprocess.run(build_cmd, cwd=root_dir, check=True)
        print("Build completed successfully! Check the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
