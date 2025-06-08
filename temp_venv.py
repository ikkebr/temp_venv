import tempfile
import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import List, Optional

class TempVenv:
    """
    A context manager that creates a temporary Python virtual environment,
    optionally installs specified packages, and activates it for the
    duration of the with block.
    """
    def __init__(
        self,
        packages: Optional[List[str]] = None,
        python_executable: Optional[str] = None,
        cleanup: bool = True,
        pip_options: Optional[List[str]] = None,
        venv_options: Optional[List[str]] = None,
        requirements_file: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initializes the TempVenv context manager.

        Args:
            packages: A list of strings specifying packages to install.
            python_executable: Path to the Python executable for the venv.
            cleanup: If True, remove the temporary directory on exit.
            pip_options: Additional options for pip install commands.
            venv_options: Additional options for venv creation.
            requirements_file: Path to a requirements.txt file.
            verbose: If True, print detailed logs.
        """
        self.packages = packages if packages is not None else []
        self.python_executable_pref = python_executable
        self.cleanup = cleanup
        self.pip_options = pip_options if pip_options is not None else []
        self.venv_options = venv_options if venv_options is not None else []
        self.requirements_file = requirements_file
        self.verbose = verbose
        self.temp_dir = None
        self.venv_python_executable = None
        self.temp_dir_path_str: Optional[str] = None

    def _find_python_executable(self) -> str:
        if self.python_executable_pref:
            if self.verbose:
                print(f"Using preferred Python executable: {self.python_executable_pref}")
            return self.python_executable_pref
        executables_to_try = [sys.executable, "python3", "python"]
        for executable in executables_to_try:
            if executable:
                try:
                    cmd = [executable, "--version"]
                    if self.verbose:
                        print(f"Attempting to use Python executable: {executable} by checking version.")
                    self._run_subprocess(cmd, "Checking Python version", python_executable_for_module=None)
                    if self.verbose:
                        print(f"Found suitable Python executable: {executable}")
                    return executable
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    if self.verbose:
                        print(f"Failed to use '{executable}': {e}")
        raise RuntimeError("Could not find a suitable Python executable.")

    def _run_subprocess(self, command: List[str], description: str, check: bool = True, capture_output: bool = True, text: bool = True, extra_env: Optional[dict] = None, python_executable_for_module: Optional[str] = None) -> subprocess.CompletedProcess:
        if python_executable_for_module:
            command = [python_executable_for_module, "-m"] + command
        if self.verbose:
            print(f"Running command for {description}: {' '.join(command)}")
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        process = subprocess.run(command, check=check, capture_output=capture_output, text=text, env=env)
        if self.verbose:
            if process.stdout:
                print(f"Stdout for {description}:\n{process.stdout.strip()}")
            if process.stderr:
                print(f"Stderr for {description}:\n{process.stderr.strip()}")
        return process

    def __enter__(self):
        if self.verbose:
            print("Creating temporary directory for virtual environment...")
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_dir_path = Path(self.temp_dir.name)
        self.temp_dir_path_str = str(temp_dir_path)
        if self.verbose:
            print(f"Temporary directory created at: {temp_dir_path}")

        try:
            base_python = self._find_python_executable() # Keep this to allow choosing a python version for uv
            if self.verbose:
                print(f"Creating virtual environment using uv (with Python {base_python}) at {temp_dir_path}...")

            venv_creation_command = ["uv", "venv", str(temp_dir_path), "--python", base_python]
            if self.venv_options:
                venv_creation_command.extend(self.venv_options)
            self._run_subprocess(venv_creation_command, "uv venv creation", python_executable_for_module=base_python)

            if os.name == "nt":
                self.venv_python_executable = temp_dir_path / "Scripts" / "python.exe"
            else:
                self.venv_python_executable = temp_dir_path / "bin" / "python"

            if not self.venv_python_executable.is_file():
                raise RuntimeError(f"Python executable not found at {self.venv_python_executable} after uv venv creation")
            if self.verbose:
                print(f"Virtual environment Python executable: {self.venv_python_executable}")

            # --- Package Installation Logic (using uv) ---
            packages_to_install = list(self.packages)
            install_commands_run = False

            if self.requirements_file:
                if Path(self.requirements_file).is_file():
                    if self.verbose:
                        print(f"Installing packages from requirements file using uv: {self.requirements_file}")
                    # Assuming 'uv pip install' is the command.
                    # We use self.venv_python_executable to ensure uv uses the venv's Python,
                    # though uv might handle this automatically when running from within a venv path.
                    # For safety, explicitly using the venv's uv/pip might be better if uv installs itself there.
                    # For now, assume 'uv' is in PATH and context-aware or can be directed.
                    cmd = ["uv", "pip", "install"] + self.pip_options + ["-r", self.requirements_file, "--python", str(self.venv_python_executable)]
                    self._run_subprocess(cmd, f"uv installing from {self.requirements_file}", python_executable_for_module=base_python)
                    install_commands_run = True
                else:
                    if self.verbose:
                         print(f"Warning: Requirements file {self.requirements_file} not found. It will be ignored.")

            if packages_to_install:
                if self.verbose:
                    print(f"Installing specified packages using uv: {', '.join(packages_to_install)}")
                cmd = ["uv", "pip", "install"] + self.pip_options + packages_to_install + ["--python", str(self.venv_python_executable)]
                self._run_subprocess(cmd, "uv installing packages", python_executable_for_module=base_python)
                install_commands_run = True

            if not install_commands_run and self.verbose:
                 print("No packages or requirements file specified for installation with uv.")

            return str(self.venv_python_executable)

        except subprocess.CalledProcessError as e:
            error_detail = f"Command '{' '.join(e.cmd)}' returned non-zero exit status {e.returncode}."
            error_detail += f"\nStdout: {e.stdout.strip()}" if e.stdout else ""
            error_detail += f"\nStderr: {e.stderr.strip()}" if e.stderr else ""
            raise RuntimeError(f"Error during virtual environment setup: {error_detail}") from e
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred during venv setup: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            if self.cleanup:
                if self.verbose:
                    print(f"Cleaning up temporary directory: {self.temp_dir.name}")
                self.temp_dir.cleanup()
                self.temp_dir = None
            else:
                if self.verbose:
                    print(f"Skipping cleanup of temporary directory: {self.temp_dir.name}")
