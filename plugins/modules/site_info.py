#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, NightLabs
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
module: site_info
short_description: List sites on a UniFi Network console
version_added: 0.1.0
description:
  - Returns the sites configured on a UniFi Network application using the official Integration API.
author:
  - NightLabs (@nightlabs-io)
options:
  site:
    description:
      - Only return this site. Without it, every site is returned.
      - Accepts the site's UUID, internal reference or display name, resolved the same way as the
        C(site) option of other modules in this collection (exact, case-sensitive match).
      - The task fails if no site matches, so this also works as a check that a site exists.
    type: str
extends_documentation_fragment:
  - nightlabs.unifi.api
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
"""

EXAMPLES = r"""
- name: List all sites
  nightlabs.unifi.site_info:
    host: 192.0.2.1
    api_key: "{{ unifi_api_key }}"
    validate_certs: false
  register: unifi_sites

- name: Get one site by its internal reference
  nightlabs.unifi.site_info:
    host: 192.0.2.1
    api_key: "{{ unifi_api_key }}"
    validate_certs: false
    site: default
  register: default_site

- name: Show its UUID
  ansible.builtin.debug:
    var: default_site.sites[0].id
"""

RETURN = r"""
sites:
  description: Sites returned by the console.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Site UUID, used by other Integration API endpoints.
      type: str
      sample: 88f7af54-98f8-306a-a1c7-c9349722b1f6
    internalReference:
      description: Short internal site name used by the legacy API.
      type: str
      sample: default
    name:
      description: Display name of the site.
      type: str
      sample: Default
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.nightlabs.unifi.plugins.module_utils.api import (
    UnifiAPIError,
    UnifiClient,
    unifi_argument_spec,
)


def main():
    argument_spec = unifi_argument_spec()
    # Optional here, unlike unifi_site_argument_spec(): without it, list every site.
    argument_spec.update(site=dict(type="str"))
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    client = UnifiClient(module)
    site = module.params["site"]
    try:
        if site:
            # Same rules as every other module: UUID, internalReference or name.
            # Fails if nothing matches, including an unknown UUID.
            sites = [client.get_site(site)]
        else:
            sites = client.get_all("/sites")
    except UnifiAPIError as e:
        module.fail_json(msg=str(e))

    module.exit_json(changed=False, sites=sites)


if __name__ == "__main__":
    main()
