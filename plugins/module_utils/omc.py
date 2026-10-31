# Copyright (C) 2026 Kristian Zarebski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""Utilities for interacting with OMC."""

import pathlib
import shutil
import subprocess
import tempfile
from collections.abc import Generator

INSTALL_SCRIPT: str = """
updatePackageIndex();
getErrorString();
installPackage({package_name}, "{package_version}", exactMatch={exact_match});
getErrorString();
"""


def get_omc() -> pathlib.Path:
    """Find OMC installation."""
    if not (_omc_install := shutil.which("omc")):
        raise FileNotFoundError("Could not find 'omc' binary.")
    return pathlib.Path(_omc_install).resolve()


def get_om_libraries() -> pathlib.Path | None:
    """Get local OMC Libraries."""
    _omc_libs = pathlib.Path.home().joinpath(".openmodelica", "libraries")
    if not _omc_libs.is_dir():
        return
    return _omc_libs


def omc_execute(command: str) -> tuple[int, str, str]:
    """Execute a command on OMC Shell."""
    _omc_binary = get_omc()
    with tempfile.NamedTemporaryFile(
        suffix=".mos", mode="w", encoding="utf-8"
    ) as temp_f:
        _ = temp_f.write(command)
        temp_f.flush()
        _result = subprocess.run(
            [f"{_omc_binary}", temp_f.name],
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
            shell=False,
        )
        return _result.returncode, _result.stdout.strip(), _result.stderr.strip()


def get_packages(
    package_name: str, package_version: str | None
) -> Generator[pathlib.Path]:
    """Get packages matching a search result."""
    if not (_omc_libs := get_om_libraries()):
        return
    _glob_ex: str = (
        f"{package_name}{'*' if not package_version else (' ' + package_version)}"
    )
    yield from _omc_libs.glob(_glob_ex)


def install_package(package_name: str, package_version: str | None) -> Generator[str]:
    _before_packages = list(get_packages(package_name, package_version))
    _exit_code, _out, _err = omc_execute(
        INSTALL_SCRIPT.format(
            package_name=package_name,
            package_version=package_version or "",
            exact_match=f"{package_version is not None}".lower(),
        )
    )
    if _exit_code != 0:
        raise RuntimeError(f"[{_exit_code}] {_err}")
    _after_packages = list(get_packages(package_name, package_version))
    if not _after_packages:
        raise RuntimeError(_out)
    return (
        package.stem for package in _after_packages if package not in _before_packages
    )


def uninstall_packages(
    package_name: str, package_version: str | None
) -> Generator[str]:
    """Remove an OM package from the system."""
    _uninstalled: list[str] = []
    for package in get_packages(package_name, package_version):
        shutil.rmtree(package)
        yield package.stem
