# zarethrex.openmodelica

[![Ansible Galaxy](https://img.shields.io/badge/galaxy-zarethrex.openmodelica-blue?logo=ansible)](https://galaxy.ansible.com/ui/repo/published/zarethrex/openmodelica/)
[![License](https://img.shields.io/badge/license-{license}-blue)](LICENSE)
[![Ansible Core](https://img.shields.io/badge/ansible--core-%3E%3D{min_ansible_version}-27a1e4?logo=ansible)](https://docs.ansible.com/)

An Ansible collection for installing [OpenModelica](https://openmodelica.org) and managing its
Modelica libraries. The collection provides a role that configures the official OSMC package
repositories and installs the toolchain, plus a module that drives the OpenModelica package
manager to install and remove Modelica libraries.

## Contents

| Type | Name | Description |
|------|------|-------------|
| Role | `zarethrex.openmodelica.install` | Configures the OSMC repository and installs OpenModelica |
| Module | `zarethrex.openmodelica.package` | Installs and removes Modelica libraries via the OpenModelica package manager |

## Requirements

- **ansible-core**: `>=2.21.0` or later
- **Target OS**: Fedora or an Enterprise Linux distribution (RHEL, CentOS Stream, AlmaLinux, Rocky Linux)
- **Python**: Python 3 on the managed node (the module executes remotely)
- **Network access** from the managed node to `build.openmodelica.org` and to the OpenModelica
  package index used by `updatePackageIndex()`

The module shells out to the `omc` binary, so it must be present on the target. In practice this
means running the `install` role first.

## Supported platforms

| Distribution | Repository channel | Tested |
|--------------|--------------------|--------|
| Fedora | `fc<major_version>` | — |
| RHEL / CentOS Stream / AlmaLinux / Rocky Linux | `el<major_version>` | CentOS Stream 10 |

The repository label is derived from the target's facts: `fc` plus
`ansible_facts.distribution_major_version` on Fedora, `el` plus the same value on every other
supported distribution.

## Installation

### From Galaxy

```bash
ansible-galaxy collection install zarethrex.openmodelica
```

### From source

```bash
git clone https://github.com/zarethrex/ansible-collection-openmodelica.git
cd ansible-collection-openmodelica
ansible-galaxy collection build
ansible-galaxy collection install zarethrex-openmodelica-*.tar.gz
```

### As a dependency

```yaml
# requirements.yml
collections:
  - name: zarethrex.openmodelica
    version: ">=0.1.0"
```

## Role: `zarethrex.openmodelica.install`

Adds the OpenModelica repository for the detected distribution and installs the OpenModelica
toolchain from it. The role is intended to run with elevated privileges.

### Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `openmodelica_install_graphical_clients` | `bool` | `true` | Whether to install the graphical applications (OMEdit and friends) |
| `openmodelica_install_cpp_runtime` | `bool` | `false` | Whether to install the alternative C++ runtime |

Further internal variables are defined in the role's `defaults/main.yml`.

### Example

```yaml
---
- name: Install OpenModelica
  hosts: all
  become: true

  roles:
    - role: zarethrex.openmodelica.install
      openmodelica_install_graphical_clients: true
      openmodelica_install_cpp_runtime: false
```

For a headless build or CI runner, disable the GUI:

```yaml
  roles:
    - role: zarethrex.openmodelica.install
      openmodelica_install_graphical_clients: false
```

## Module: `zarethrex.openmodelica.package`

Installs or removes Modelica libraries by driving the OpenModelica package manager. The module
refreshes the package index, calls `installPackage()`, and verifies the result against the
contents of the OpenModelica library directory. Dependency resolution is delegated to the
package manager, so installing a library also brings in its declared dependencies.

### Parameters

| Parameter | Type | Required | Default | Choices | Description |
|-----------|------|----------|---------|---------|-------------|
| `name` | `list` of `str` | yes | — | — | Library name or names. A bare string is accepted and treated as a single-element list. Append `==<version>` to pin a version. |
| `state` | `str` | no | `present` | `present`, `absent` | Whether the library should be installed or removed. |
| `version` | `str` | no | `null` | — | Reserved. Version pinning is performed through the `name` parameter (see below). |

### Version pinning

Versions are specified inline on the library name:

```yaml
- name: Install a specific version
  zarethrex.openmodelica.package:
    name: Buildings==14.0.0
```

The `==` separator is split on the first occurrence, and surrounding whitespace is trimmed, so
`name: "Buildings == 14.0.0"` behaves the same way. Without a version, the package manager
selects the newest available release.

Note that the version string must correspond to a version the package manager recognises. Some
libraries publish post-release builds whose directory names carry extra metadata (for example
`14.0.0+maint.om`); check the available versions before pinning.

### Return values

| Key | Type | Description |
|-----|------|-------------|
| `changed` | `bool` | Whether any library was installed or removed |
| `packages` | `list` | The `name` values exactly as supplied |
| `packages_installed` | `list` | Returned when `state: present` |
| `packages_removed` | `list` | Returned when `state: absent` |
| `omc_executable` | `str` | Resolved path to the `omc` binary |
| `omc_libraries` | `str` | Resolved OpenModelica library directory |

### Check mode

The module supports check mode. It reports whether a change would occur without contacting the
package manager or modifying the library directory.

### Examples

```yaml
- name: Install the Modelica Standard Library
  zarethrex.openmodelica.package:
    name: Modelica

- name: Install a pinned version
  zarethrex.openmodelica.package:
    name: Buildings==14.0.0

- name: Install several libraries in one task
  zarethrex.openmodelica.package:
    name:
      - Modelica
      - Buildings==14.0.0
    state: present

- name: Remove a library
  zarethrex.openmodelica.package:
    name: Buildings
    state: absent

- name: Dry run
  zarethrex.openmodelica.package:
    name: Buildings
  check_mode: true
```

## Putting it together

```yaml
---
- name: Provision an OpenModelica workstation
  hosts: openmodelica_nodes
  become: true

  roles:
    - role: zarethrex.openmodelica.install
      openmodelica_install_graphical_clients: true
      openmodelica_install_cpp_runtime: false

  tasks:
    - name: Install Modelica libraries
      zarethrex.openmodelica.package:
        name:
          - Modelica
          - Buildings==14.0.0
        state: present
```

## Limitations

- **Linux and macOS only.** The module resolves the library directory as
  `~/.openmodelica/libraries`. On Windows, OpenModelica uses
  `%AppData%\.openmodelica\libraries`, which is not currently handled.
- **No dependency-aware removal.** Removing a library deletes its directory. The package manager
  performs no reverse-dependency check, so removing a library that others declare in their `uses`
  annotations will cause load failures later.
- **The `version` parameter is not yet wired up.** Use the `name: <library>==<version>` form.

## Testing

The collection is tested with Molecule. Scenarios live under `extensions/molecule/`.

```bash
pip install molecule molecule-plugins[docker,podman] ansible-lint yamllint
molecule test
```

## License

GPL-3.0-or-later — see the [LICENSE](LICENSE) file for details.

## Author

Kristian Zarebski
