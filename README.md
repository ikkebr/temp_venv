# temp_venv
A context manager that creates a temporary Python virtual environment, optionally installs specified packages, and activates it for the duration of the with block.

## Installation

You can install `temp-venv` from PyPI using pip:

```bash
pip install temp-venv
```

## Temporary Virtual Environment Context Manager (`TempVenv`)

This repository provides a Python context manager, `TempVenv`, that simplifies the creation and management of temporary Python virtual environments. It's useful for scenarios where you need to run scripts or commands in an isolated environment with specific dependencies, without manually creating and cleaning up virtual environments.

### Features

-   Creates a temporary virtual environment.
-   Optionally installs a list of specified packages (e.g., `requests`, `numpy==1.20.0`) into the environment.
-   Provides the path to the Python executable within the temporary environment.
-   Automatically cleans up the virtual environment (deletes the temporary directory) upon exiting the `with` block by default.
-   Offers options for verbose logging, custom Python executables, pip and venv flags, and installation via requirements files.

## API Reference

### Class `TempVenv`

Constructs a `TempVenv` object.

*   `packages: Optional[List[str]] = None`: A list of packages to install (e.g., `["requests", "numpy==1.23.5"]`). Defaults to `None`.
*   `python_executable: Optional[str] = None`: Specifies the full path to a Python executable to be used for creating the virtual environment. If `None`, the script will attempt to find a suitable Python executable (e.g., `sys.executable`, `python3`, `python`). Defaults to `None`.
*   `cleanup: bool = True`: If `True`, the temporary directory containing the virtual environment is automatically deleted when the context manager exits. If `False`, the directory is left behind (you may need to clean it up manually). Defaults to `True`.
*   `pip_options: Optional[List[str]] = None`: A list of additional options to pass to `pip install` (e.g., `["--no-cache-dir"]`). Defaults to `None`.
*   `venv_options: Optional[List[str]] = None`: A list of additional options to pass to the `venv` creation command (e.g., `["--copies"]`). Defaults to `None`.
*   `requirements_file: Optional[str] = None`: Path to a `requirements.txt` file from which to install packages. Defaults to `None`.
*   `verbose: bool = False`: If `True`, enables verbose output, printing commands executed and their results to stdout/stderr. Useful for debugging. Defaults to `False`.

### Prerequisites

-   Python 3.9+
-   `uv`

### Usage

The primary component is the `TempVenv` class located in `temp_venv.py`.

```python
from temp_venv import TempVenv
import subprocess
import sys
import os # Needed for Example 3 file operations

# Example 1: Create a temporary venv and install specific packages with verbose output
print("Example 1: Using TempVenv with 'requests', 'numpy==1.23.5', 'multiext', and verbose=True")
try:
    with TempVenv(packages=["requests", "numpy==1.23.5", "multiext"], verbose=True) as venv_python:
        print(f"  Inside TempVenv: Python executable is {venv_python}")

        print("  Running script to check requests version (verbose output from TempVenv should be visible above)...")
        script_requests = "import requests; print(f'  Requests version: {requests.__version__}')"
        subprocess.run([venv_python, "-c", script_requests], check=True, text=True)

        print("  Running script to check numpy version...")
        script_numpy = "import numpy; print(f'  Numpy version: {numpy.__version__}')"
        subprocess.run([venv_python, "-c", script_numpy], check=True, text=True)

        print("  Running script to check multiext version...")
        script_multiext = "import multiext; print(f'  multiext version: {multiext.__version__}')"
        subprocess.run([venv_python, "-c", script_multiext], check=True, text=True)

    print("  TempVenv context exited. Environment has been cleaned up.")

except RuntimeError as e:
    print(f"Error during Example 1: {e}")
except Exception as e:
    print(f"An unexpected error occurred during Example 1: {e}")

print("\n" + "="*50 + "\n")

# Example 2: Create a temporary venv with cleanup=False
print("Example 2: Using TempVenv with no additional packages and cleanup=False")
temp_dir_path_for_example2 = None
try:
    # The TempVenv instance itself is the context manager, here assigned to 'venv_context'
    with TempVenv(cleanup=False, verbose=True) as venv_python: # venv_python is the path to the executable
        print(f"  Inside TempVenv: Python executable is {venv_python}")
        # To get the temp_dir_path, you'd typically access it from the TempVenv object if it stores it,
        # or know it from verbose logs. For this example, we'll just note it should persist.
        # temp_dir_path_for_example2 = venv_context.temp_dir_path_str # If TempVenv instance was captured and exposed it
        # The verbose output from TempVenv will show the temporary directory path.
        print(f"  The temporary directory (shown in verbose logs above) should NOT be cleaned up automatically.")
        subprocess.run([venv_python, "-c", "print('  Hello from the temporary venv that will persist!')"], check=True, text=True)
    print("  TempVenv context exited. Environment should NOT have been cleaned up.")
    print("  Manual cleanup would be needed for the directory mentioned in the verbose logs if this were a real scenario.")
    # In a real script, if you captured the TempVenv instance:
    # if temp_dir_path_for_example2 and os.path.exists(temp_dir_path_for_example2):
    #     print(f"  Manually cleaning up {temp_dir_path_for_example2} now for the sake of example completion.")
    #     shutil.rmtree(temp_dir_path_for_example2)


except RuntimeError as e:
    print(f"Error during Example 2: {e}")
    # Add shutil import if manual cleanup is actually implemented in example
    # import shutil
except Exception as e:
    print(f"An unexpected error occurred during Example 2: {e}")

print("\n" + "="*50 + "\n")

# Example 3: Using the venv's Python to run an external script
print("Example 3: Running an external script with TempVenv")
# Create a dummy external script
external_script_content = """
import sys
import six # This will be installed by TempVenv

print(f"Hello from external_script.py running with {sys.executable}")
print(f"Six version: {six.__version__}")
"""
external_script_name = "my_script_requiring_packages.py"
with open(external_script_name, "w") as f:
    f.write(external_script_content)

try:
    with TempVenv(packages=["six==1.15.0"]) as venv_python_executable:
        print(f"  Inside TempVenv: Python executable is {venv_python_executable}")
        print(f"  Running '{external_script_name}' which requires 'six==1.15.0'")
        subprocess.run([venv_python_executable, external_script_name], check=True, text=True)
    print(f"  TempVenv context exited. '{external_script_name}' and venv are cleaned up (script is not part of venv).")

except RuntimeError as e:
    print(f"Error during Example 3: {e}")
except Exception as e: # Catch broader exceptions for script file operations
    print(f"An unexpected error occurred during Example 3: {e}")
finally:
    # Clean up the dummy script
    if os.path.exists(external_script_name):
        os.remove(external_script_name)
        print(f"  Cleaned up '{external_script_name}'.")

print("\n" + "="*50 + "\n")

# Example 4: Using a requirements file, pip_options and venv_options
print("Example 4: Using TempVenv with a requirements.txt, pip_options, and verbose output")
requirements_content = """
pyjokes # For a bit of fun
requests==2.25.0
# A comment to ensure parsing works
tinydb>=3.0,<5.0
"""
requirements_filename = "temp_requirements_example.txt"
with open(requirements_filename, "w") as f:
    f.write(requirements_content)

try:
    with TempVenv(
        requirements_file=requirements_filename,
        packages=["six"], # Also add 'six' from packages list
        pip_options=["--no-cache-dir"],
        venv_options=["--copies"], # Use --copies instead of --system-site-packages for easier testing
        verbose=True,
        cleanup=True
    ) as venv_python:
        print(f"  Inside TempVenv: Python executable is {venv_python}")
        script_to_run = """
import pyjokes, requests, six, tinydb
print(f'    pyjokes version: {pyjokes.__version__}')
print(f'    requests version: {requests.__version__}')
print(f'    six version: {six.__version__}')
print(f'    tinydb version: {tinydb.__version__}')
"""
        subprocess.run([venv_python, "-c", script_to_run], check=True, text=True)
    print(f"  TempVenv context exited. '{requirements_filename}' was used and venv cleaned up.")
except RuntimeError as e:
    print(f"Error during Example 4: {e}")
finally:
    if os.path.exists(requirements_filename):
        os.remove(requirements_filename)
        print(f"  Cleaned up '{requirements_filename}'.")

print("\nScript finished.")
```

### Running Tests

Unit tests are located in `test_temp_venv.py`. You can run them using:

```bash
python -m unittest test_temp_venv.py
```
Alternatively, use `python -m unittest discover -s . -p "test_temp_venv.py"` for discovery, which is what the GitHub Actions workflow uses.

This will execute a series of tests to ensure the `TempVenv` class functions correctly, including environment creation, package installation (specific versions, multiple packages), isolation, cleanup, and handling of various options like `requirements_file`, `verbose`, `pip_options`, etc.
