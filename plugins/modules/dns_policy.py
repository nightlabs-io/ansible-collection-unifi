#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, John Cuckovich
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
  - A record is found by its O(record_type), its O(domain) and, for types that allow several
    records on one domain, the options that tell those records apart. The other options are
    the record's attributes, which an update changes.
  - "Identity by type: V(A_RECORD), V(AAAA_RECORD) and V(CNAME_RECORD) by domain alone;
    V(MX_RECORD) by O(mail_server_domain); V(TXT_RECORD) by O(text); V(SRV_RECORD) by
    O(service), O(protocol) and O(server_domain); V(FORWARD_DOMAIN) by O(ip_address)."
  - A record of another type on the same domain is a different record, and is left alone.
  - Only the options that are set are compared and sent; an option left unset keeps the value
    already on the console.
author:
  - John Cuckovich (@jpcuckovi)
options:
  domain:
    description:
      - Domain name of the record, for example C(app.example.lan).
      - For V(SRV_RECORD), the base name; the console serves the record at
        C(<service>.<protocol>.<domain>).
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
      - Required in both states, because records of different types can share a domain.
      - Each option below names the types it belongs to; setting it with any other type fails.
    type: str
    required: true
    choices: [A_RECORD, AAAA_RECORD, CNAME_RECORD, MX_RECORD, TXT_RECORD, SRV_RECORD, FORWARD_DOMAIN]
  ipv4_address:
    description:
      - IPv4 address the domain resolves to.
      - Belongs to V(A_RECORD). Required to create one.
    type: str
  ipv6_address:
    description:
      - IPv6 address the domain resolves to.
      - Belongs to V(AAAA_RECORD). Required to create one.
    type: str
  target_domain:
    description:
      - Domain name the record points to.
      - Belongs to V(CNAME_RECORD). Required to create one.
    type: str
  mail_server_domain:
    description:
      - Domain name of the mail server.
      - Belongs to V(MX_RECORD), and identifies it. Always required.
    type: str
    version_added: 0.2.0
  text:
    description:
      - Text of the record. Compared case-sensitively.
      - Belongs to V(TXT_RECORD), and identifies it. Always required.
      - Changing the text creates another record; remove the old one with O(state=absent).
    type: str
    version_added: 0.2.0
  service:
    description:
      - Service name, with its leading underscore, for example C(_ldap).
      - Belongs to V(SRV_RECORD), and identifies it. Always required.
    type: str
    version_added: 0.2.0
  protocol:
    description:
      - Protocol, with its leading underscore, for example C(_tcp).
      - Belongs to V(SRV_RECORD), and identifies it. Always required.
    type: str
    version_added: 0.2.0
  server_domain:
    description:
      - Domain name of the server that provides the service.
      - Belongs to V(SRV_RECORD), and identifies it. Always required.
    type: str
    version_added: 0.2.0
  service_port:
    description:
      - Port the service listens on, sent to the API as C(port).
      - Not named C(port), which is the console's own port (O(port)).
      - Belongs to V(SRV_RECORD). Required to create one.
    type: int
    version_added: 0.2.0
  priority:
    description:
      - Priority of the record; lower values are preferred.
      - Belongs to V(MX_RECORD) and V(SRV_RECORD). Required to create either.
    type: int
    version_added: 0.2.0
  weight:
    description:
      - Relative weight among SRV records of equal priority.
      - Belongs to V(SRV_RECORD). Required to create one.
    type: int
    version_added: 0.2.0
  ip_address:
    description:
      - IPv4 or IPv6 address of the DNS server that queries for the domain are forwarded to.
      - Belongs to V(FORWARD_DOMAIN), and identifies it. Always required.
      - Several forwards can share a domain, one per address.
    type: str
    version_added: 0.2.0
  enabled:
    description:
      - Whether the record is active.
      - When unset, a new record is created enabled and an existing record keeps its current state.
    type: bool
  ttl_seconds:
    description:
      - Time to live of the record, in seconds.
      - Belongs to V(A_RECORD), V(AAAA_RECORD) and V(CNAME_RECORD); the console stores no TTL
        for the other types.
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
- name: Create an A record
  nightlabs.unifi.dns_policy:
    record_type: A_RECORD
    domain: app.example.lan
    ipv4_address: 192.0.2.10
    ttl_seconds: 3600
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default

- name: Change only the address of that record; enabled and TTL keep their current values
  nightlabs.unifi.dns_policy:
    record_type: A_RECORD
    domain: app.example.lan
    ipv4_address: 192.0.2.20
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default

- name: Point a CNAME at it
  nightlabs.unifi.dns_policy:
    record_type: CNAME_RECORD
    domain: www.example.lan
    target_domain: app.example.lan
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default

- name: Two mail servers for one domain, each its own record
  nightlabs.unifi.dns_policy:
    record_type: MX_RECORD
    domain: example.lan
    mail_server_domain: "{{ item.server }}"
    priority: "{{ item.priority }}"
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default
  loop:
    - {server: mail1.example.lan, priority: 10}
    - {server: mail2.example.lan, priority: 20}

- name: A TXT record on the same domain
  nightlabs.unifi.dns_policy:
    record_type: TXT_RECORD
    domain: example.lan
    text: v=spf1 mx -all
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default

- name: An SRV record, served at _ldap._tcp.example.lan
  nightlabs.unifi.dns_policy:
    record_type: SRV_RECORD
    domain: example.lan
    service: _ldap
    protocol: _tcp
    server_domain: ldap.example.lan
    service_port: 389
    priority: 10
    weight: 5
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default

- name: Forward queries for a domain to another DNS server
  nightlabs.unifi.dns_policy:
    record_type: FORWARD_DOMAIN
    domain: corp.example
    ip_address: 192.0.2.53
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default

- name: Delete one of the MX records; the other and the TXT record stay
  nightlabs.unifi.dns_policy:
    record_type: MX_RECORD
    domain: example.lan
    mail_server_domain: mail2.example.lan
    state: absent
    api_key: "{{ unifi_api_key }}"
    host: 192.0.2.1
    site: default
"""

RETURN = r"""
policy:
  description:
    - The DNS policy as stored on the console after the task.
    - Holds the fields of its own type only.
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
      sample: app.example.lan
    enabled:
      description: Whether the record is active.
      type: bool
      sample: true
    ipv4Address:
      description: IPv4 address the domain resolves to.
      type: str
      returned: when the record type is C(A_RECORD)
      sample: 192.0.2.10
    ipv6Address:
      description: IPv6 address the domain resolves to.
      type: str
      returned: when the record type is C(AAAA_RECORD)
      sample: 2001:db8::10
    targetDomain:
      description: Domain name the record points to.
      type: str
      returned: when the record type is C(CNAME_RECORD)
      sample: app.example.lan
    ttlSeconds:
      description: Time to live of the record, in seconds.
      type: int
      returned: when the record type is C(A_RECORD), C(AAAA_RECORD) or C(CNAME_RECORD)
      sample: 14400
    mailServerDomain:
      description: Domain name of the mail server.
      type: str
      returned: when the record type is C(MX_RECORD)
      sample: mail1.example.lan
    text:
      description: Text of the record.
      type: str
      returned: when the record type is C(TXT_RECORD)
      sample: v=spf1 mx -all
    serverDomain:
      description: Domain name of the server that provides the service.
      type: str
      returned: when the record type is C(SRV_RECORD)
      sample: ldap.example.lan
    service:
      description: Service name.
      type: str
      returned: when the record type is C(SRV_RECORD)
      sample: _ldap
    protocol:
      description: Protocol.
      type: str
      returned: when the record type is C(SRV_RECORD)
      sample: _tcp
    port:
      description: Port the service listens on.
      type: int
      returned: when the record type is C(SRV_RECORD)
      sample: 389
    priority:
      description: Priority of the record.
      type: int
      returned: when the record type is C(MX_RECORD) or C(SRV_RECORD)
      sample: 10
    weight:
      description: Relative weight among SRV records of equal priority.
      type: int
      returned: when the record type is C(SRV_RECORD)
      sample: 5
    ipAddress:
      description: Address of the DNS server that queries are forwarded to.
      type: str
      returned: when the record type is C(FORWARD_DOMAIN)
      sample: 192.0.2.53
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


# Each per-type option and the API field it is sent as.
FIELDS = {
    "ipv4_address": "ipv4Address",
    "ipv6_address": "ipv6Address",
    "target_domain": "targetDomain",
    "mail_server_domain": "mailServerDomain",
    "text": "text",
    "service": "service",
    "protocol": "protocol",
    "server_domain": "serverDomain",
    "service_port": "port",
    "priority": "priority",
    "weight": "weight",
    "ip_address": "ipAddress",
    "ttl_seconds": "ttlSeconds",
}

# Per type: `identity` tells apart records of that type on one domain, so it is required
# in both states; `attributes` are what an update changes. Taken from live records: one
# domain may hold several MX, TXT, SRV and forward records, and several types at once.
RECORD_TYPES = {
    "A_RECORD": {"identity": (), "attributes": ("ipv4_address", "ttl_seconds")},
    "AAAA_RECORD": {"identity": (), "attributes": ("ipv6_address", "ttl_seconds")},
    "CNAME_RECORD": {"identity": (), "attributes": ("target_domain", "ttl_seconds")},
    "MX_RECORD": {"identity": ("mail_server_domain",), "attributes": ("priority",)},
    "TXT_RECORD": {"identity": ("text",), "attributes": ()},
    "SRV_RECORD": {"identity": ("service", "protocol", "server_domain"), "attributes": ("service_port", "priority", "weight")},
    "FORWARD_DOMAIN": {"identity": ("ip_address",), "attributes": ()},
}

# DNS names compare case-insensitively; TXT text does not.
CASE_SENSITIVE = ("text",)


def main():
    argument_spec = unifi_argument_spec()
    argument_spec.update(unifi_site_argument_spec())
    argument_spec.update(
        domain=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        record_type=dict(type="str", required=True, choices=list(RECORD_TYPES)),
        enabled=dict(type="bool"),
        ipv4_address=dict(type="str"),
        ipv6_address=dict(type="str"),
        target_domain=dict(type="str"),
        mail_server_domain=dict(type="str"),
        text=dict(type="str"),
        service=dict(type="str"),
        protocol=dict(type="str"),
        server_domain=dict(type="str"),
        service_port=dict(type="int"),
        priority=dict(type="int"),
        weight=dict(type="int"),
        ip_address=dict(type="str"),
        ttl_seconds=dict(type="int"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[["record_type", name, list(spec["identity"])]
                     for name, spec in RECORD_TYPES.items() if spec["identity"]],
        supports_check_mode=True,
    )

    params = module.params
    record_type = params["record_type"]
    domain = params["domain"].lower()
    spec = RECORD_TYPES[record_type]
    own_options = spec["identity"] + spec["attributes"]

    # An option of another type would be compared against a field the record never has,
    # so every run would report changed. required_if cannot forbid options, hence this check.
    stray = [option for option in FIELDS if option not in own_options and params[option] is not None]
    if stray:
        module.fail_json(msg="%s cannot be set when record_type is %s" % (", ".join(stray), record_type))

    identity = {FIELDS[option]: params[option] for option in spec["identity"]}
    label = " ".join([record_type, domain] + ["%s=%s" % kv for kv in identity.items()])

    client = UnifiClient(module)

    try:
        site_id = client.resolve_site(params["site"])
        policy = client.resolve_policy(site_id, record_type, domain, identity, case_sensitive=CASE_SENSITIVE)
        path = "/sites/%s/dns/policies" % site_id

        if params["state"] == "absent":
            if policy is None:
                module.exit_json(changed=False, msg="DNS policy %s not found. No action performed." % label)
            if not module.check_mode:
                client.request("%s/%s" % (path, policy["id"]), method="DELETE")
            module.exit_json(changed=True, msg="DNS policy %s %s." % (label, "would be deleted" if module.check_mode else "deleted"))

        data = dict(identity, type=record_type, domain=domain, enabled=params["enabled"])
        data.update({FIELDS[option]: params[option] for option in spec["attributes"]})
        data = {k: v for k, v in data.items() if v is not None}

        if policy is None:
            # Defaults for a new record; every other attribute must be given.
            data.setdefault("enabled", True)
            if "ttl_seconds" in own_options:
                data.setdefault("ttlSeconds", 14400)
            missing = [option for option in spec["attributes"] if FIELDS[option] not in data]
            if missing:
                module.fail_json(msg="Creating %s requires %s." % (label, ", ".join(missing)))
            if module.check_mode:
                module.exit_json(changed=True, msg="DNS policy %s would be created." % label)
            response = client.request(path, method="POST", body=data)
            module.exit_json(changed=True, policy=response, msg="DNS policy %s created." % label)

        # id and metadata are not sent back; set aside to return an unchanged record whole.
        metadata = policy.pop("metadata", None)
        policy_id = policy.pop("id")
        update = policy | data
        if update == policy:
            module.exit_json(changed=False, policy=dict(update, id=policy_id, metadata=metadata),
                             msg="DNS policy %s is up to date." % label)
        if module.check_mode:
            module.exit_json(changed=True, msg="DNS policy %s would be updated." % label)
        response = client.request("%s/%s" % (path, policy_id), method="PUT", body=update)
        module.exit_json(changed=True, policy=response, msg="DNS policy %s updated." % label)

    except UnifiAPIError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
