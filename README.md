# nightlabs.unifi

Ansible modules for UniFi Network consoles (UniFi Cloud Gateway, Dream Machine, Cloud Key),
built on the official UniFi Network Integration API (`/proxy/network/integration/v1`).

## Modules

| Module                            | Description                                                                    |
| --------------------------------- | ------------------------------------------------------------------------------ |
| `nightlabs.unifi.site_info`       | List sites, or look up one site by UUID, internal reference or display name    |
| `nightlabs.unifi.device_info`     | List the adopted devices on a site, or get the full detail of one device       |
| `nightlabs.unifi.dns_policy_info` | List the DNS policies (local DNS records) on a site, or get one policy         |
| `nightlabs.unifi.dns_policy`      | Create, update or delete a DNS policy of any type the Network app offers       |

The `_info` modules are read-only. `dns_policy` is idempotent: it changes only the fields a task
sets, and reports `changed` only when the console differed. All modules support check mode. Full
documentation for each module:

```
ansible-doc nightlabs.unifi.<module>
```

## Requirements

- ansible-core at the version declared as `requires_ansible` in `meta/runtime.yml`.
- Python 3.9 or later on the host that runs the modules: normally the controller, or the
  execution environment when run from AWX.
- A UniFi Network API key, created in the Network app under
  Settings > Control Plane > Integrations.

## Installation

The collection is installed from git. In a `requirements.yml`:

```yaml
collections:
  - name: https://github.com/jpcuckovi/ansible-collection-unifi.git
    type: git
    version: main
```

```
ansible-galaxy collection install -r requirements.yml
```

Setting `version` to a release tag instead of `main` pins the collection to that release.

## Connection options

Every module takes the same connection options:

| Option           | Default | Environment variable   | Notes                                                            |
| ---------------- | ------- | ---------------------- | ---------------------------------------------------------------- |
| `host`           |         | `UNIFI_HOST`           | Required. Hostname or IP address of the console                  |
| `api_key`        |         | `UNIFI_API_KEY`        | Required. Never logged                                           |
| `validate_certs` | `true`  | `UNIFI_VALIDATE_CERTS` | Set to `false` for the console's factory self-signed certificate |
| `port`           | `443`   |                        |                                                                  |
| `timeout`        | `30`    |                        | Seconds per request                                              |

The modules form the action group `nightlabs.unifi.unifi`, so the options can be set once
per play with `module_defaults` instead of on every task.

## Examples

```yaml
- name: List the A records on the default site
  hosts: localhost
  gather_facts: false

  module_defaults:
    group/nightlabs.unifi.unifi:
      host: "{{ unifi_host }}"
      api_key: "{{ unifi_api_key }}"
      validate_certs: false

  tasks:
    - name: Get every DNS policy
      nightlabs.unifi.dns_policy_info:
        site: default
      register: dns

    - name: Show each A record as name -> address
      ansible.builtin.debug:
        msg: "{{ item.domain }} -> {{ item.ipv4Address }}"
      loop: "{{ dns.policies | selectattr('type', 'equalto', 'A_RECORD') }}"
      loop_control:
        label: "{{ item.id }}"
```

Records are managed with `dns_policy`, which finds each one by its type, its domain
and, where one domain can hold several records of a type, the fields that tell them
apart (the module documentation lists them). A rerun with the same values reports no
change, and a value left unset keeps what the console already has:

```yaml
- name: Publish a host and an alias for it
  hosts: localhost
  gather_facts: false

  module_defaults:
    group/nightlabs.unifi.unifi:
      host: "{{ unifi_host }}"
      api_key: "{{ unifi_api_key }}"
      validate_certs: false

  tasks:
    - name: Point app.example.lan at its host
      nightlabs.unifi.dns_policy:
        site: default
        domain: app.example.lan
        record_type: A_RECORD
        ipv4_address: 192.0.2.10

    - name: Add www.example.lan as an alias for it
      nightlabs.unifi.dns_policy:
        site: default
        domain: www.example.lan
        record_type: CNAME_RECORD
        target_domain: app.example.lan

    - name: Remove a record that is no longer needed
      nightlabs.unifi.dns_policy:
        site: default
        domain: old.example.lan
        record_type: A_RECORD
        state: absent
```

With `--check`, the same play reports what it would change without changing it.

## Sites

Modules that work on a site take a `site` option, which accepts the site's UUID, its internal
reference (`default` for the default site) or its display name. The internal reference does not
change when a site is renamed, so it is the most stable choice for playbooks.

## Known limitations

- `dns_policy_info` returns only DNS records created as DNS policies. Records generated from a
  client's Local DNS Record setting (on a client with a fixed IP address) appear in the Network
  app's DNS Records list but are not returned by the Integration API.
- `dns_policy` identifies a record by its type, its domain and its identifying fields, so a
  change to any of those is a different record: the task creates it and leaves the old one in
  place. Remove the old one with `state: absent`.

## Development

The commands below run from the collection root, which must sit at a path ending in
`ansible_collections/nightlabs/unifi` for `ansible-test` to find it.

Sanity tests (documentation, argument specs, code style):

```
ansible-test sanity --venv
```

Unit tests (no console needed):

```
ansible-test units --venv
```

Integration tests need a live console. Before the first run, copy
`tests/integration/integration_config.yml.template` to `tests/integration/integration_config.yml`
and fill it in; that file is gitignored. The targets are marked `unsupported` so that runs
without a console skip them:

```
ansible-test integration --allow-unsupported
```

## License

GNU General Public License v3.0 or later. See [LICENSE](LICENSE).
