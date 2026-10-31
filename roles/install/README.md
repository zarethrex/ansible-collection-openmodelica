# Ansible Role - OpenModelica

This role installs [OpenModelica](https://openmodelica.org/) on the system, works on RHEL and Debian based systems, install customisation via variables only supported in Debian.

## Requirements

- `ansible-core >= 2.21`

## Role Variables

### Install OpenModelica Graphical Clients (Debian Only)

Install OMEdit and other graphical clients, if `false` install only OpenModelica Compiler (OMC).

`openmodelica_install_graphical_clients: true`

### Install OpenModelica C++ Runtime (Debian Only)

Install alternative to the C runtime.

`openmodelica_install_cpp_runtime: false`

## Dependencies

None

## Example Playbook

```yaml
- name: Install OpenModelica
  hosts: debian_servers
  vars:
     openmodelica_install_graphical_clients: true
  roles:
     - zarethrex.openmodelica.install
```

## License

GPLv3-or-later
