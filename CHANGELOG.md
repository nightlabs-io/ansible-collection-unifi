# Changelog

## 0.1.0 (unreleased)

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
