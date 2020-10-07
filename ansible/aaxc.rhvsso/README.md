Role Name
=========

This role enable Red Hat Single Sign On / Keycloak on Red Hat Virtualization / OVirt 4.4

Requirements
------------

- none

Role Variables
--------------

- sso_server_name:   The SSO/keycloak server name, like "sso.example.com"
- sso_server_port:   The port at which the SSO/keycloak server is reachable, like "443"
- sso_realm:         The SSO/keycloak realm that OVirt should use, like "example"
- sso_client_id:     The name of the client in SSO/keycloak, like "ovirt-engine"
- sso_client_secret: The client secret key from SSO/keycloak, something like "e7e86376-8807-4cc3-89a8-ec672f03873d"

Dependencies
------------
- none

Example Playbook
----------------

    - hosts: servers
      roles:
         - { role: aaxc.rhvsso }

License
-------

BSD

Author Information
------------------

