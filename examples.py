import sys
import subprocess
import os
import shutil
from pathlib import Path
from temp_venv import TempVenv # Assuming TempVenv will be importable from this new structure

if __name__ == '__main__':
    print("Starting script in the global environment...")
    subprocess.run([sys.executable, "-c", "import sys; print(f'Global Python: {sys.executable}')"])

    print("\nExample 1: TempVenv with 'requests', 'numpy', verbose=True")
    try:
        with TempVenv(packages=["requests", "numpy==1.23.5"], verbose=True) as venv_python:
            print(f"Inside TempVenv: Python executable is {venv_python}")
            subprocess.run([venv_python, "-c", "import requests; print(f'Requests version: {requests.__version__}')"], check=True)
            subprocess.run([venv_python, "-c", "import numpy; print(f'Numpy version: {numpy.__version__}')"], check=True)
        print("\nTempVenv context exited. Environment should be clean.")
    except Exception as e:
        print(f"An error occurred: {e}")

    print("\nExample 2: TempVenv with ensure_pip=False, verbose=True")
    try:
        with TempVenv(packages=["a-package-that-will-not-be-installed"], ensure_pip=False, verbose=True) as venv_python:
            print(f"Inside TempVenv (ensure_pip=False): Python executable is {venv_python}")
            print(f"Attempting to run: {venv_python} -m pip --version")
            result = subprocess.run([venv_python, "-m", "pip", "--version"], capture_output=True, text=True)
            if result.returncode == 0: print(f"Pip --version check SUCCEEDED unexpectedly: {result.stdout}")
            else: print(f"Pip --version check FAILED as expected: {result.stderr.strip()}")

            print("Attempting to import 'a-package-that-will-not-be-installed'...")
            try:
                subprocess.run([venv_python, "-c", "import ensure_pip_test_package_not_installed"], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"Successfully failed to import non-existent package: {e.stderr.strip()}")
        print("\nTempVenv (ensure_pip=False) context exited.")
    except Exception as e:
        print(f"An error occurred in ensure_pip=False example: {e}")

    print("\nExample 3: TempVenv with requirements file, verbose=True, cleanup=False")
    requirements_content = "Django==3.2\ncolorama==0.4.4" # A known older version for stability
    temp_req_file_path = "temp_requirements_main.txt"
    with open(temp_req_file_path, "w") as f: f.write(requirements_content)

    venv_mgr_example3 = TempVenv(requirements_file=temp_req_file_path, verbose=True, cleanup=False)
    try:
        with venv_mgr_example3 as venv_python:
            print(f"Inside TempVenv (req file, no cleanup): Python is {venv_python}")
            subprocess.run([venv_python, "-c", "import django; print(f'Django version: {django.get_version()}')"], check=True)
            print(f"Temp venv directory {venv_mgr_example3.temp_dir_path_str} should still exist.")
        print(f"\nTempVenv (req file, no cleanup) exited. Dir {venv_mgr_example3.temp_dir_path_str} should persist.")
        if Path(venv_mgr_example3.temp_dir_path_str).exists():
             print(f"Directory {venv_mgr_example3.temp_dir_path_str} correctly persists.")
             shutil.rmtree(venv_mgr_example3.temp_dir_path_str) # Manual cleanup for example
             print(f"Manually cleaned up {venv_mgr_example3.temp_dir_path_str}.")
        else:
            print(f"ERROR: Directory {venv_mgr_example3.temp_dir_path_str} was unexpectedly cleaned up.")

    except Exception as e:
        print(f"An error occurred with requirements file example: {e}")
        if venv_mgr_example3.temp_dir_path_str and Path(venv_mgr_example3.temp_dir_path_str).exists(): # Cleanup if error
            shutil.rmtree(venv_mgr_example3.temp_dir_path_str)
            print(f"Cleaned up {venv_mgr_example3.temp_dir_path_str} due to error.")
    finally:
        if os.path.exists(temp_req_file_path): os.remove(temp_req_file_path)

    print("\nScript finished.")
