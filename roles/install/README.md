# Ansible Role - OpenModelica

This role installs [OpenModelica](https://openmodelica.org/) on the system.

## Requirements

None

## Role Variables

### Install OpenModelica Graphical Clients

Install OMEdit and other graphical clients, if `false` install only OpenModelica Compiler (OMC).

`openmodelica_install_graphical_clients: true`

### Install OpenModelica C++ Runtime

Install alternative to the C runtime.

`openmodelica_install_cpp_runtime: false`

### Install OpenModelica Packages
A list of OpenModelica packages and their versions to install.

`openmodelica_packages: []`

## Dependencies

None

## Example Playbook

```yaml
- name: Install OpenModelica
  hosts: servers
  vars:
     openmodelica_install_graphical_clients: true
  roles:
     - zarethrex.openmodelica
```

## License

MIT
