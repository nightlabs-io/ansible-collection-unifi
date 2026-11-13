# Changelog

## 0.2.0 (unreleased)

### Breaking changes

- `dns_policy`: `record_type` is required in both states, because one domain can hold records
  of several types. A task with `state: absent` must now name the type, and the identifying
  options of types that have them.
- `dns_policy`: a task naming another type for an existing domain no longer fails with
  "Cannot change type"; it creates a record of that type beside the existing one.

### Minor changes

- `dns_policy`: manages `MX_RECORD`, `TXT_RECORD`, `SRV_RECORD` and `FORWARD_DOMAIN` policies,
  with the new options `mail_server_domain`, `text`, `service`, `protocol`, `server_domain`,
  `service_port`, `priority`, `weight` and `ip_address`.
- `dns_policy`: a record is found by its type, its domain and the fields that tell apart records
  of that type on one domain, so several MX, TXT, SRV and forward records can share a domain.
- `dns_policy`: an update no longer needs the record's value; for example `enabled: false` alone
  pauses an existing A record. Creating a record still requires every attribute without a default.
- `dns_policy`: `ttl_seconds` is accepted only for A, AAAA and CNAME records, the types that
  have a TTL.
- `dns_policy_info`: documents the fields of every record type.
- The repository moved to https://github.com/jpcuckovi/ansible-collection-unifi. GitHub redirects
  the old URL, but `requirements.yml` git sources should be updated to the new one.

## 0.1.0 (2026-11-12)

### New modules

- `nightlabs.unifi.site_info`: list sites, or look up one site by UUID, internal reference or
  display name.
- `nightlabs.unifi.device_info`: list the adopted devices on a site, or get the full detail of one
  device by UUID.
- `nightlabs.unifi.dns_policy_info`: list the DNS policies on a site, or get one policy by UUID.
- `nightlabs.unifi.dns_policy`: create, update or delete an A, AAAA or CNAME DNS policy on a site,
  identified by its domain. Supports check mode.

### Other

- Modules require Python 3.9 or later on the host that runs them.
- All modules share the connection options `host`, `api_key`, `port`, `validate_certs` and
  `timeout`, with environment-variable fallbacks for `host`, `api_key` and `validate_certs`.
- All modules belong to the `nightlabs.unifi.unifi` action group for use with `module_defaults`.
