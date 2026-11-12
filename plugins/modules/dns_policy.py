#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, NightLabs
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
module: dns_policy
short_description: Manage DNS policies on a UniFi Network site
version_added: 0.1.0
description:
  - Creates, updates or deletes a local DNS record, stored as a DNS policy, on one site of a
    UniFi Network application, using the official Integration API.
  - These are the records under C(Policy Table > DNS Records) in the Network app.
  - The record is identified by O(domain). Only the options that are set are compared and sent;
    an option left unset keeps the value already on the console.
author:
  - NightLabs (@nightlabs-io)
options:
  domain:
    description:
      - Domain name of the record, for example C(app.example.lan).
      - Matched case-insensitively against existing records, and sent in lowercase.
    type: str
    required: true
  state:
    description:
      - V(present) creates the record, or updates it when it exists and differs.
      - V(absent) deletes the record when it exists.
    type: str
    choices: [present, absent]
    default: present
  record_type:
    description:
      - Type of the record.
      - Required when O(state=present).
      - The type of an existing record cannot be changed; the task fails instead. Delete the
        record first to recreate it with another type.
    type: str
    choices: [A_RECORD, AAAA_RECORD, CNAME_RECORD]
  ipv4_address:
    description:
      - IPv4 address the domain resolves to.
      - Required when O(record_type=A_RECORD), and not allowed with any other type.
    type: str
  ipv6_address:
    description:
      - IPv6 address the domain resolves to.
      - Required when O(record_type=AAAA_RECORD), and not allowed with any other type.
    type: str
  target_domain:
    description:
      - Domain name the record points to.
      - Required when O(record_type=CNAME_RECORD), and not allowed with any other type.
    type: str
  enabled:
    description:
      - Whether the record is active.
      - When unset, a new record is created enabled and an existing record keeps its current state.
    type: bool
  ttl_seconds:
    description:
      - Time to live of the record, in seconds.
      - When unset, a new record is created with C(14400) and an existing record keeps its current value.
    type: int
extends_documentation_fragment:
  - nightlabs.unifi.api
  - nightlabs.unifi.api.site
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
    support: full
seealso:
  - module: nightlabs.unifi.dns_policy_info
"""

EXAMPLES = r"""
- name: Create A_RECORD DNS Policy
  nightlabs.unifi.dns_policy:
    record_type: A_RECORD
    domain: example.com
    enabled: true
    ipv4_address: 192.0.2.1
    ttl_seconds: 14400
    state: present
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    validate_certs: false
    site: default
  register: unifi_policy

- name: Create CNAME_RECORD DNS Policy
  nightlabs.unifi.dns_policy:
    record_type: CNAME_RECORD
    domain: example-two.com
    target_domain: example-three.com
    enabled: true
    ttl_seconds: 14400
    state: present
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    validate_certs: false
    site: default
  register: unifi_policy

- name: Change only the address of an existing A record; enabled and TTL keep their current values
  nightlabs.unifi.dns_policy:
    record_type: A_RECORD
    domain: example.com
    ipv4_address: 192.0.2.2
    state: present
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    validate_certs: false
    site: default
  register: unifi_policy

- name: Delete a DNS Policy
  nightlabs.unifi.dns_policy:
    domain: example.com
    state: absent
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    validate_certs: false
    site: default
"""

RETURN = r"""
policy:
  description:
    - The DNS policy as stored on the console after the task.
  returned: when O(state=present), except in check mode when a change would be made
  type: dict
  contains:
    type:
      description: Type of the record.
      type: str
      sample: A_RECORD
    id:
      description: Policy UUID, as used by M(nightlabs.unifi.dns_policy_info) and other Integration API endpoints.
      type: str
      sample: 3f1c2a9e-5b7d-4e8f-9a1b-2c3d4e5f6a7b
    domain:
      description: Domain name of the record, in lowercase.
      type: str
      sample: example.com
    enabled:
      description: Whether the record is active.
      type: bool
      sample: true
    ipv4Address:
      description: IPv4 address the domain resolves to.
      type: str
      returned: when the record type is C(A_RECORD)
      sample: 192.0.2.1
    ipv6Address:
      description: IPv6 address the domain resolves to.
      type: str
      returned: when the record type is C(AAAA_RECORD)
      sample: 2001:db8::10
    targetDomain:
      description: Domain name the record points to.
      type: str
      returned: when the record type is C(CNAME_RECORD)
      sample: example-three.com
    ttlSeconds:
      description: Time to live of the record, in seconds.
      type: int
      sample: 14400
    metadata:
      description: Information about how the record was created.
      type: dict
      contains:
        origin:
          description: Who created the record. V(USER_DEFINED) for records added in the app or through this API.
          type: str
          sample: USER_DEFINED
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.nightlabs.unifi.plugins.module_utils.api import (
    UnifiAPIError,
    UnifiClient,
    unifi_argument_spec,
    unifi_site_argument_spec,
)


# The option that holds each record type's value, and the API key it is sent as.
VALUE_OPTIONS = {
    "A_RECORD": ("ipv4_address", "ipv4Address"),
    "AAAA_RECORD": ("ipv6_address", "ipv6Address"),
    "CNAME_RECORD": ("target_domain", "targetDomain"),
}


def main():
    argument_spec = unifi_argument_spec()
    argument_spec.update(unifi_site_argument_spec())
    argument_spec.update(
        domain=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        record_type=dict(type="str", choices=list(VALUE_OPTIONS)),
        ipv4_address=dict(type="str"),
        ipv6_address=dict(type="str"),
        target_domain=dict(type="str"),
        enabled=dict(type="bool"),
        ttl_seconds=dict(type="int"),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           required_if=[
                               ["state", "present", ["record_type"]],
                               ["record_type", "A_RECORD", ["ipv4_address"]],
                               ["record_type", "AAAA_RECORD", ["ipv6_address"]],
                               ["record_type", "CNAME_RECORD", ["target_domain"]],
                           ],
                           supports_check_mode=True)

    client = UnifiClient(module)

    if module.params["state"] == "present":
        record_type = module.params["record_type"]
        value_option, value_key = VALUE_OPTIONS[record_type]

        # A value for another type would be compared against a field the record never has,
        # so every run would report changed. required_if cannot forbid options, hence this check.
        other_options = [option for option, key in VALUE_OPTIONS.values() if option != value_option]
        stray = [option for option in other_options if module.params[option] is not None]
        if stray:
            module.fail_json(msg="%s cannot be set when record_type is %s" % (", ".join(stray), record_type))

        data = {
            "type": record_type,
            "enabled": module.params["enabled"],
            "domain": module.params["domain"].lower(),
            "ttlSeconds": module.params["ttl_seconds"],
            value_key: module.params[value_option],
        }

        data = {k: v for k, v in data.items() if v is not None}

    try:
        site_id = client.resolve_site(module.params["site"])
        policy = client.resolve_policy(site_id, module.params["domain"])

        if policy is not None and module.params["state"] == "present":
            path = "/sites/%s/dns/policies/%s" % (site_id, policy['id'])

            metadata = policy.pop("metadata", None)
            policy_id = policy.pop("id", None)

            update = (policy | data)
            update_required = update != policy

            if update["type"] != policy["type"]:
                module.fail_json(msg=f"Cannot change type of DNS policy from {policy['type']} to {update['type']}")

            if update_required:
                if not module.check_mode:
                    response = client.request(path, method="PUT", body=update)
                    module.exit_json(changed=True, policy=response, msg=f"DNS Policy {module.params['domain']} updated.")
                else:
                    module.exit_json(changed=True, msg=f"DNS Policy {module.params['domain']} would be updated.")
            else:
                update["id"] = policy_id
                update["metadata"] = metadata
                module.exit_json(changed=False, policy=update, msg=f"DNS Policy {module.params['domain']} is up to date.")

        elif policy is not None and module.params["state"] == "absent":
            if not module.check_mode:
                path = "/sites/%s/dns/policies/%s" % (site_id, policy['id'])
                client.request(path, method="DELETE")
                module.exit_json(changed=True, msg=f"DNS Policy {module.params['domain']} deleted.")
            else:
                module.exit_json(changed=True, msg=f"DNS Policy {module.params['domain']} would be deleted.")

        elif policy is None and module.params["state"] == "present":
            if not module.check_mode:
                data.setdefault("enabled", True)
                data.setdefault("ttlSeconds", 14400)
                path = "/sites/%s/dns/policies" % site_id
                response = client.request(path, method="POST", body=data)
                module.exit_json(changed=True, policy=response, msg=f"DNS Policy {module.params['domain']} created.")
            else:
                module.exit_json(changed=True, msg=f"DNS Policy {module.params['domain']} would be created.")

        elif policy is None and module.params["state"] == "absent":
            module.exit_json(changed=False, msg=f"DNS Policy {module.params['domain']} not found. No action performed.")

    except UnifiAPIError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
