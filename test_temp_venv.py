import unittest
import subprocess
import os
import sys
import shutil
import tempfile
import io
import contextlib # For redirect_stdout/stderr
from pathlib import Path
from temp_venv import TempVenv # Assuming temp_venv.py is in the same directory or PYTHONPATH

class TestTempVenv(unittest.TestCase):

    def test_venv_creation_and_cleanup(self):
        """Test basic venv creation and that the directory is cleaned up."""
        temp_dir_path_obj = None
        # To check cleanup properly, we need to ensure TempVenv is not created in current dir
        # tempfile.TemporaryDirectory handles this by using system's temp location.
        with TempVenv() as venv_python:
            self.assertTrue(Path(venv_python).is_file(), "Python executable does not exist")
            self.assertTrue(os.access(venv_python, os.X_OK), "Python executable is not executable")
            venv_root_path = Path(venv_python).parent.parent
            self.assertTrue(venv_root_path.is_dir(), "Venv root directory does not exist during context")
            temp_dir_path_obj = venv_root_path
        self.assertTrue(temp_dir_path_obj is not None, "Venv path was not captured")
        self.assertFalse(temp_dir_path_obj.exists(),
                         f"Temporary venv directory '{temp_dir_path_obj}' was not cleaned up.")

    def test_package_installation(self):
        package_to_install = "six"
        with TempVenv(packages=[package_to_install]) as venv_python:
            script = f"import {package_to_install}; print({package_to_install}.__version__)"
            result = subprocess.run([venv_python, "-c", script], capture_output=True, text=True, check=True)
            self.assertTrue(any(char.isdigit() for char in result.stdout.strip()),
                            f"No version number found in output for {package_to_install}: {result.stdout.strip()}")

    def test_specific_package_version(self):
        package_name = "requests"
        package_version = "2.25.0"
        with TempVenv(packages=[f"{package_name}=={package_version}"]) as venv_python:
            script = f"import {package_name}; print({package_name}.__version__)"
            result = subprocess.run([venv_python, "-c", script], capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), package_version)

    def test_no_packages(self):
        with TempVenv() as venv_python:
            self.assertTrue(Path(venv_python).is_file())
            result = subprocess.run([venv_python, "-c", "print('Hello from basic venv')"],
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), "Hello from basic venv")

    def test_venv_isolation(self):
        non_existent_package = "a_truly_non_existent_package_abcdef12345"
        with TempVenv() as venv_python:
            script = f"import {non_existent_package}"
            result = subprocess.run([venv_python, "-c", script], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ModuleNotFoundError", result.stderr)

    def test_multiple_packages(self):
        packages_to_install = ["six", "requests==2.25.0"]
        with TempVenv(packages=packages_to_install) as venv_python:
            script_six = "import six; print(six.__version__)"
            result_six = subprocess.run([venv_python, "-c", script_six], capture_output=True, text=True, check=True)
            self.assertTrue(any(char.isdigit() for char in result_six.stdout))
            script_requests = "import requests; print(requests.__version__)"
            result_requests = subprocess.run([venv_python, "-c", script_requests],
                                             capture_output=True, text=True, check=True)
            self.assertEqual(result_requests.stdout.strip(), "2.25.0")

    def test_invalid_package_name(self):
        invalid_package = "thispackagedoesnotexistandshouldfailpipinstall"
        with self.assertRaises(RuntimeError) as context:
            with TempVenv(packages=[invalid_package]):
                pass
        self.assertIn("Error during virtual environment setup", str(context.exception))
        self.assertIn(invalid_package, str(context.exception))

    def test_custom_python_executable(self):
        with TempVenv(python_executable=sys.executable, packages=["six"]) as venv_python:
            self.assertTrue(Path(venv_python).is_file())
            subprocess.run([venv_python, "-c", "import six"], check=True)
        if self.get_verbose_setting_from_env(): print(f"Tested with python_executable: {sys.executable}")


    def get_verbose_setting_from_env(self):
        # Helper to avoid print statements if not running tests verbosely from CLI
        return os.environ.get("UNITTEST_VERBOSE") == "TRUE"


    def test_cleanup_false(self):
        temp_dir_to_check = None
        venv_manager = TempVenv(cleanup=False, packages=["six"], verbose=self.get_verbose_setting_from_env())
        try:
            with venv_manager as venv_executable_path:
                temp_dir_to_check = venv_manager.temp_dir_path_str
                self.assertIsNotNone(temp_dir_to_check)
                self.assertTrue(Path(temp_dir_to_check).is_dir())
                self.assertTrue(Path(venv_executable_path).is_file())
                subprocess.run([str(venv_executable_path), "-c", "import six"], check=True)
            self.assertIsNotNone(temp_dir_to_check)
            self.assertTrue(Path(temp_dir_to_check).is_dir(),
                            f"Temporary directory '{temp_dir_to_check}' should still exist.")
        finally:
            if temp_dir_to_check and Path(temp_dir_to_check).is_dir():
                if self.get_verbose_setting_from_env(): print(f"Manually cleaning up {temp_dir_to_check} for test_cleanup_false")
                shutil.rmtree(temp_dir_to_check)

    def test_pip_options(self):
        with TempVenv(packages=["pyjokes"], pip_options=["--no-cache-dir", "--compile"]) as venv_python:
            self.assertTrue(Path(venv_python).is_file())
            subprocess.run([venv_python, "-c", "import pyjokes; print(pyjokes.get_joke())"], check=True)

    def test_venv_options(self):
        with TempVenv(packages=["tinydb"], venv_options=["--copies"]) as venv_python:
            self.assertTrue(Path(venv_python).is_file())
            subprocess.run([venv_python, "-c", "import tinydb; print(tinydb.__version__)"], check=True)

    def test_requirements_file(self):
        package_in_req = "pyjokes"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp_req_file:
            tmp_req_file.write(f"{package_in_req}\n")
            tmp_req_file_path = tmp_req_file.name
        try:
            with TempVenv(requirements_file=tmp_req_file_path) as venv_python:
                self.assertTrue(Path(venv_python).is_file())
                subprocess.run([venv_python, "-c", f"import {package_in_req}; print({package_in_req}.get_joke())"], check=True)
        finally:
            os.remove(tmp_req_file_path)

    def test_requirements_file_and_packages_argument(self):
        package_in_req = "pyjokes"
        package_in_arg = "tinydb"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp_req_file:
            tmp_req_file.write(f"{package_in_req}\n")
            tmp_req_file_path = tmp_req_file.name
        try:
            with TempVenv(requirements_file=tmp_req_file_path, packages=[package_in_arg]) as venv_python:
                self.assertTrue(Path(venv_python).is_file())
                subprocess.run([venv_python, "-c", f"import {package_in_req}; print({package_in_req}.get_joke())"], check=True)
                subprocess.run([venv_python, "-c", f"import {package_in_arg}; print({package_in_arg}.__version__)"], check=True)
        finally:
            os.remove(tmp_req_file_path)

    def test_requirements_file_not_found(self):
        non_existent_req_file = "non_existent_requirements.txt"
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture): # Capture stdout for verbose output
            with TempVenv(requirements_file=non_existent_req_file, verbose=True): # verbose=True to generate the warning
                pass
        output = stdout_capture.getvalue()
        self.assertIn(f"Warning: Requirements file {non_existent_req_file} not found. It will be ignored.", output)

        # Test with verbose=False, no error should occur
        with TempVenv(requirements_file=non_existent_req_file, verbose=False):
            pass


    def test_verbose_output(self):
        package_to_install = "six"
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            with TempVenv(packages=[package_to_install], verbose=True) as venv_python:
                subprocess.run([venv_python, "-c", "import six; print('six imported')"], check=True)
        output = stdout_capture.getvalue() + stderr_capture.getvalue()

        expected_phrases = [
            "Creating temporary directory", "Found suitable Python executable",
            "Creating virtual environment using", "Running command for venv creation:",
            "-m venv --without-pip",
            "ensure_pip is True", # Part of the new logic
            "downloading get-pip.py", "installing pip with get-pip.py",
            "upgrading pip, setuptools, wheel",
            f"Installing specified packages: {package_to_install}", # Adjusted for current log
            f"-m pip install {package_to_install}",
            "Cleaning up temporary directory"
        ]
        for phrase in expected_phrases:
            self.assertIn(phrase, output)

    def test_verbose_output_cleanup_false(self):
        stdout_capture = io.StringIO()
        temp_dir_path = None
        venv_manager = TempVenv(verbose=True, cleanup=False)
        try:
            with contextlib.redirect_stdout(stdout_capture):
                with venv_manager as venv_executable_path:
                    temp_dir_path = venv_manager.temp_dir_path_str
                    self.assertTrue(Path(venv_executable_path).is_file())
            output = stdout_capture.getvalue()
            self.assertIsNotNone(temp_dir_path)
            self.assertIn(f"Skipping cleanup of temporary directory: {temp_dir_path}", output)
            self.assertTrue(Path(temp_dir_path).exists())
        finally:
            if temp_dir_path and Path(temp_dir_path).exists():
                if self.get_verbose_setting_from_env(): print(f"Manually cleaning up {temp_dir_path} for test_verbose_output_cleanup_false")
                shutil.rmtree(temp_dir_path)

    def test_ensure_pip_false_no_pip_initially(self):
        package_to_try_install = "six"
        # Capture stdout to check verbose messages
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            with TempVenv(ensure_pip=False, packages=[package_to_try_install], verbose=True) as venv_python_path:
                self.assertTrue(Path(venv_python_path).is_file())
                pip_check_command = [venv_python_path, "-m", "pip", "--version"]
                result = subprocess.run(pip_check_command, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no module named pip", result.stderr.lower(), f"stderr: {result.stderr}")
                import_script = f"import {package_to_try_install}"
                import_result = subprocess.run([venv_python_path, "-c", import_script], capture_output=True, text=True)
                self.assertNotEqual(import_result.returncode, 0)
                self.assertIn("ModuleNotFoundError", import_result.stderr)
        output = stdout_capture.getvalue()
        self.assertIn("ensure_pip is False. Skipping pip download, installation, and upgrade.", output)
        self.assertIn("Skipping package installation because pip is not available", output)


    def test_ensure_pip_true_explicitly(self):
        package_to_install = "pyjokes"
        with TempVenv(ensure_pip=True, packages=[package_to_install], verbose=True) as venv_python_path:
            self.assertTrue(Path(venv_python_path).is_file())
            pip_check_command = [venv_python_path, "-m", "pip", "--version"]
            result = subprocess.run(pip_check_command, capture_output=True, text=True, check=True)
            self.assertIn("pip", result.stdout.lower())
            self.assertTrue(any(char.isdigit() for char in result.stdout))
            script = f"import {package_to_install}; print({package_to_install}.get_joke())"
            pkg_run_result = subprocess.run([venv_python_path, "-c", script], capture_output=True, text=True, check=True)
            self.assertTrue(len(pkg_run_result.stdout.strip()) > 0)

    def test_ensure_pip_false_with_existing_pip_in_base_venv(self):
        # This test's behavior depends on whether the system's 'venv' module, when run with
        # '--without-pip', *truly* excludes pip. If it doesn't, this test would change meaning.
        # Assuming '--without-pip' works as advertised, pip should not be present.
        with TempVenv(ensure_pip=False, verbose=True) as venv_python_path: # No packages needed
            self.assertTrue(Path(venv_python_path).is_file())
            pip_check_command = [venv_python_path, "-m", "pip", "--version"]
            result = subprocess.run(pip_check_command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, "pip should not be present with ensure_pip=False and venv created --without-pip.")
            # This is the corrected assertion string
            self.assertIn("no module named pip", result.stderr.lower(), f"stderr: {result.stderr}")

if __name__ == '__main__':
    # Add a way to pass verbosity from environment for make test_verbose
    if os.environ.get("UNITTEST_VERBOSE") == "TRUE":
        unittest.main(verbosity=2)
    else:
        unittest.main()
