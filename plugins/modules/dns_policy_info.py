#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, NightLabs
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
module: dns_policy_info
short_description: List DNS policies on a UniFi Network site
version_added: 0.1.0
description:
  - Returns the local DNS records created as DNS policies on one site of a UniFi Network application,
    using the official Integration API.
  - These are the records added under C(Policy Table > DNS Records) in the Network app.
author:
  - NightLabs (@nightlabs-io)
options:
  policy:
    description:
      - Only return this DNS policy. Without it, every DNS policy on the site is returned.
      - UUID of the policy, as returned in RV(policies[].id).
      - The task fails if the site has no DNS policy with this UUID.
    type: str
extends_documentation_fragment:
  - nightlabs.unifi.api
  - nightlabs.unifi.api.site
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
notes:
  - Only DNS records created as DNS policies are returned. Records generated from a client's
    C(Local DNS Record) setting (on a client with a fixed IP address) appear in the Network app's
    DNS Records list but are not returned by this API endpoint, so the app can show more DNS records
    than this module returns.
"""

EXAMPLES = r"""
- name: List every DNS policy on the default site
  nightlabs.unifi.dns_policy_info:
    host: 192.0.2.1
    api_key: "{{ unifi_api_key }}"
    validate_certs: false
    site: default
  register: unifi_dns

- name: Show each A record as name -> address
  ansible.builtin.debug:
    msg: "{{ item.domain }} -> {{ item.ipv4Address }}"
  loop: "{{ unifi_dns.policies | selectattr('type', 'equalto', 'A_RECORD') }}"
  loop_control:
    label: "{{ item.id }}"

- name: Show each CNAME as alias -> target
  ansible.builtin.debug:
    msg: "{{ item.domain }} -> {{ item.targetDomain }}"
  loop: "{{ unifi_dns.policies | selectattr('type', 'equalto', 'CNAME_RECORD') }}"
  loop_control:
    label: "{{ item.id }}"
"""

RETURN = r"""
policies:
  description:
    - DNS policies on the site. Always a list, with one element when O(policy) is set and empty when the site has none.
    - Which address field is present depends on RV(policies[].type).
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: UUID of the DNS policy.
      type: str
      sample: 3f1c2a9e-5b7d-4e8f-9a1b-2c3d4e5f6a7b
    type:
      description: Record type, for example V(A_RECORD), V(AAAA_RECORD) or V(CNAME_RECORD).
      type: str
      sample: A_RECORD
    domain:
      description: The name the record answers for.
      type: str
      sample: host.example.lan
    enabled:
      description: Whether the record is active. V(false) when the record is paused in the Network app.
      type: bool
      sample: true
    ttlSeconds:
      description: Record TTL in seconds. V(0) means the Network app's C(Auto) TTL.
      type: int
      sample: 0
    metadata:
      description: Information about how the record was created.
      type: dict
      contains:
        origin:
          description: Who created the record. V(USER_DEFINED) for records added by hand.
          type: str
          sample: USER_DEFINED
    ipv4Address:
      description: IPv4 address the name resolves to.
      type: str
      returned: when RV(policies[].type) is V(A_RECORD)
      sample: 192.0.2.10
    ipv6Address:
      description: IPv6 address the name resolves to.
      type: str
      returned: when RV(policies[].type) is V(AAAA_RECORD)
      sample: 2001:db8::10
    targetDomain:
      description: Name the alias points to.
      type: str
      returned: when RV(policies[].type) is V(CNAME_RECORD)
      sample: target.example.lan
"""

from ansible.module_utils.basic import AnsibleModule
from uuid import UUID

from ansible_collections.nightlabs.unifi.plugins.module_utils.api import (
    UnifiAPIError,
    UnifiClient,
    UnifiNotFoundError,
    unifi_argument_spec,
    unifi_site_argument_spec,
)


def main():
    argument_spec = unifi_argument_spec()
    argument_spec.update(unifi_site_argument_spec())
    argument_spec.update(policy=dict(type="str", required=False))
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    client = UnifiClient(module)
    policy = module.params["policy"]
    try:
        site_id = client.resolve_site(module.params["site"])
        path = "/sites/%s/dns/policies" % site_id
        if policy:
            policy_id = str(UUID(policy))
            policies = [client.request("%s/%s" % (path, policy_id))]
        else:
            policies = client.get_all(path)
    except UnifiNotFoundError:
        module.fail_json(msg="Policy not found")
    except ValueError as e:
        module.fail_json(msg="Invalid UUID for policy: %s" % e)
    except UnifiAPIError as e:
        module.fail_json(msg=str(e))

    module.exit_json(changed=False, policies=policies)


if __name__ == "__main__":
    main()
