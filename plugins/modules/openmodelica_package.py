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
"""Manage OpenModelica packages."""

import subprocess
import typing

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.zarethrex.openmodelica.plugins.module_utils.omc import (
    get_om_libraries,
    get_omc,
    get_packages,
    install_package,
    uninstall_packages,
)

DOCUMENTATION = r"""
module: openmodelica_package
short_description: Install and remove Modelica libraries
description:
  - Installs or removes Modelica libraries via the OpenModelica package manager.
  - Refreshes the package index before installation.
  - Delegates dependency resolution to the package manager.
  - Supports installing multiple libraries in one task.
author:
  - Kristian Zarebski
options:
  name:
    description:
      - Library name or names.
      - A bare string is treated as a single library.
      - Append C(==<version>) to pin a specific version.
      - Surrounding whitespace is trimmed automatically.
    type: list
    elements: str
    required: true
    sample:
      - Modelica
      - Buildings==14.0.0
  version:
    description:
      - Reserved for future use.
      - Currently unused; use C(name=<library>==<version>) for version pinning instead.
    type: str
    required: false
    default: null
  state:
    description:
      - Whether the library should be installed or removed.
    type: str
    required: false
    default: present
    choices:
      - present
      - absent
seealso:
  - module: ansible.builtin.package
    description: Generic package module for cross-platform package management.
"""

EXAMPLES = r"""
- name: Install the Modelica Standard Library
  zarethrex.openmodelica.openmodelica_package:
    name: Modelica

- name: Install a specific version
  zarethrex.openmodelica.openmodelica_package:
    name: Buildings==14.0.0

- name: Install several libraries at once
  zarethrex.openmodelica.openmodelica_package:
    name:
      - Modelica
      - Buildings
      - Complex
    state: present

- name: Remove a library
  zarethrex.openmodelica.package:
    name: Buildings
    state: absent

- name: Dry run without making changes
  zarethrex.openmodelica.openmodelica_package:
    name: Buildings
  check_mode: true

- name: Install after role execution
  hosts: all
  become: true
  roles:
    - role: zarethrex.openmodelica.install
  tasks:
    - name: Install modelica libraries
      zarethrex.openmodelica.openmodelica_package:
        name:
          - Modelica
          - Buildings==14.0.0
"""

RETURN = r"""
packages:
  description: The library names exactly as supplied.
  type: list
  returned: always
  sample: ['Modelica', 'Buildings==14.0.0']
changed:
  description: Whether any change was made.
  type: bool
  returned: always
  sample: true
packages_installed:
  description: The library names that were installed.
  type: list
  returned: when state is C(present) and changed
  sample: ['Modelica 4.1.0', 'Buildings 14.0.0']
packages_removed:
  description: The library names that were removed.
  type: list
  returned: when state is C(absent) and changed
  sample: ['Buildings 14.0.0']
omc_executable:
  description: Resolved path to the C(omc) binary.
  type: str
  returned: always
  sample: /opt/openmodelica/bin/omc
omc_libraries:
  description: Resolved OpenModelica library directory.
  type: str
  returned: always
  sample: /root/.openmodelica/libraries
std_err:
  description: Stderr from the OMC subprocess. Only present on failure.
  type: str
  returned: when failure
  sample: '[...notification: Package installed successfully...]'
"""


def main() -> None:
    _arguments: dict[str, typing.Any] = {
        "name": {
            "type": "list",
            "elements": "str",
            "required": True,
        },
        "version": {"type": "str", "required": False, "default": None},
        "state": {
            "type": "str",
            "required": False,
            "default": "present",
            "choices": ["present", "absent"],
        },
    }
    _module = AnsibleModule(argument_spec=_arguments, supports_check_mode=True)

    _packages: list[str] = _module.params["name"]
    _package_state: typing.Literal["absent", "present"] = _module.params["state"]

    _omc = get_omc()
    _omc_libs = get_om_libraries()

    _return_info: dict[str, str | bool | None | list[str]] = {
        "packages": _packages,
        "omc_executable": f"{_omc}",
        "omc_libraries": f"{_omc_libs}",
        "changed": False,
    }
    _package_names: list[str] = []
    _package_versions: list[str | None] = []
    for package in _packages:
        _package_name: str = package
        _package_version: str | None = None
        if "==" in package:
            _package_name, _package_version = package.split("==", 1)
            _package_name = _package_name.strip()
            _package_version = _package_version.strip()
        _package_names.append(_package_name)
        _package_versions.append(_package_version)

        _package_installed: bool = (
            next(get_packages(_package_name, _package_version), None) is not None
        )

        _change_required: bool = (
            _package_state == "absent" and _package_installed
        ) or (_package_state == "present" and not _package_installed)

        _return_info["changed"] = _return_info["changed"] or _change_required

    if _module.check_mode or not _return_info["changed"]:
        _module.exit_json(**_return_info)

    if _package_state == "present":
        for _name, _version in zip(_package_names, _package_versions):
            try:
                _installed: list[str] = list(install_package(_name, _version))
            except subprocess.CalledProcessError as exc:
                _module.fail_json(
                    msg="Failed to install package.",
                    exception=exc,
                    std_err=exc.stderr,
                    package_name=_name,
                    package_version=_version,
                    **_return_info,
                )
            except (
                subprocess.TimeoutExpired,
                FileNotFoundError,
            ) as exc:
                _module.fail_json(
                    msg="Failed to install package.",
                    exception=exc,
                    package_name=_name,
                    package_version=_version,
                    **_return_info,
                )
            if not _installed:
                _module.fail_json(
                    msg="OMC package install failed, package not found in library.",
                    exception=None,
                    **_return_info,
                )
        _module.exit_json(packages_installed=_packages, **_return_info)

    for _name, _version in zip(_package_names, _package_versions):
        try:
            _uninstalled: list[str] = list(uninstall_packages(_name, _version))
        except Exception as exc:
            _module.fail_json(
                msg="Failed to delete packages.", exception=exc, **_return_info
            )
    _module.exit_json(
        packages_removed=_packages,
        **_return_info,
    )


if __name__ in "__main__":
    main()
