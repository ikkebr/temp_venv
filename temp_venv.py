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
        ensure_pip: bool = True,  # Added ensure_pip
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
            ensure_pip: If True, ensure pip is installed (via get-pip.py if needed).
                        If False, skip pip installation/upgrade.
        """
        self.packages = packages if packages is not None else []
        self.python_executable_pref = python_executable
        self.cleanup = cleanup
        self.pip_options = pip_options if pip_options is not None else []
        self.venv_options = venv_options if venv_options is not None else []
        self.requirements_file = requirements_file
        self.verbose = verbose
        self.ensure_pip = ensure_pip  # Store ensure_pip
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
                    self._run_subprocess(cmd, "Checking Python version")
                    if self.verbose:
                        print(f"Found suitable Python executable: {executable}")
                    return executable
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    if self.verbose:
                        print(f"Failed to use '{executable}': {e}")
        raise RuntimeError("Could not find a suitable Python executable.")

    def _run_subprocess(self, command: List[str], description: str, check: bool = True, capture_output: bool = True, text: bool = True, extra_env: Optional[dict] = None) -> subprocess.CompletedProcess:
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
            base_python = self._find_python_executable()
            if self.verbose:
                print(f"Creating virtual environment using {base_python} at {temp_dir_path}...")

            venv_creation_command = [base_python, "-m", "venv", "--without-pip", str(temp_dir_path)]
            if self.venv_options:
                venv_creation_command.extend(self.venv_options)
            self._run_subprocess(venv_creation_command, "venv creation")

            if os.name == "nt":
                self.venv_python_executable = temp_dir_path / "Scripts" / "python.exe"
            else:
                self.venv_python_executable = temp_dir_path / "bin" / "python"

            if not self.venv_python_executable.is_file():
                raise RuntimeError(f"Python executable not found at {self.venv_python_executable}")
            if self.verbose:
                print(f"Virtual environment Python executable: {self.venv_python_executable}")

            # --- Pip Installation Logic ---
            pip_check_initial = self._run_subprocess([str(self.venv_python_executable), "-m", "pip", "--version"], "checking for initial pip", check=False)
            pip_initially_available = pip_check_initial.returncode == 0

            pip_available_for_package_install = False

            if not self.ensure_pip:
                if self.verbose:
                    print("ensure_pip is False. Skipping pip download, installation, and upgrade.")
                if pip_initially_available:
                    if self.verbose:
                        print("pip was already present in the venv (created without --without-pip or base Python includes it).")
                    pip_available_for_package_install = True
                else:
                    if self.verbose and (self.packages or self.requirements_file):
                        print("Warning: ensure_pip is False and pip is not initially available. Package installation will be skipped.")
                    pip_available_for_package_install = False
            else: # self.ensure_pip is True
                if not pip_initially_available:
                    if self.verbose:
                        print("ensure_pip is True and pip is not initially available. Attempting to install via get-pip.py.")
                    get_pip_path = temp_dir_path / "get-pip.py"
                    self._run_subprocess(["curl", "-sS", "https://bootstrap.pypa.io/get-pip.py", "-o", str(get_pip_path)], "downloading get-pip.py")
                    self._run_subprocess([str(self.venv_python_executable), str(get_pip_path)], "installing pip with get-pip.py")
                    if self.verbose:
                         print("pip installed successfully via get-pip.py.")
                else:
                    if self.verbose:
                        print("ensure_pip is True and pip is already available. Skipping get-pip.py download and installation.")

                if self.verbose:
                    print("Upgrading pip, setuptools, and wheel...")
                self._run_subprocess([str(self.venv_python_executable), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], "upgrading pip, setuptools, wheel")
                pip_available_for_package_install = True

            # --- Package Installation Logic ---
            if pip_available_for_package_install:
                packages_to_install = list(self.packages)
                install_commands_run = False

                if self.requirements_file:
                    if Path(self.requirements_file).is_file():
                        if self.verbose:
                            print(f"Installing packages from requirements file: {self.requirements_file}")
                        cmd = [str(self.venv_python_executable), "-m", "pip", "install"] + self.pip_options + ["-r", self.requirements_file]
                        self._run_subprocess(cmd, f"installing from {self.requirements_file}")
                        install_commands_run = True
                    else:
                        if self.verbose:
                             print(f"Warning: Requirements file {self.requirements_file} not found. It will be ignored.")

                if packages_to_install:
                    if self.verbose:
                        print(f"Installing specified packages: {', '.join(packages_to_install)}")
                    cmd = [str(self.venv_python_executable), "-m", "pip", "install"] + self.pip_options + packages_to_install
                    self._run_subprocess(cmd, "installing packages")
                    install_commands_run = True

                if not install_commands_run and self.verbose : # No packages or req file, but pip is available
                     print("pip is available, but no packages or requirements file specified for installation.")

            elif (self.packages or self.requirements_file) and self.verbose: # Pip not available, but packages were requested
                print("Skipping package installation because pip is not available (ensure_pip=False and pip not initially present).")

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
