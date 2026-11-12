# Plugins

| Directory        | Contents                                                                                                                   |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `modules/`       | One file per module. Each builds its argument spec, calls the API client and returns JSON                                  |
| `module_utils/`  | `api.py`: the `UnifiClient` HTTP client and the shared argument specs. Ansible bundles it into each module that imports it |
| `doc_fragments/` | `api.py`: shared option documentation, merged into a module's docs through `extends_documentation_fragment`                |

## Conventions

- Every module starts its argument spec from `unifi_argument_spec()` (the connection options) and
  documents them with the `nightlabs.unifi.api` fragment.
- `unifi_site_argument_spec()` defines `site` as required, for modules that act on exactly one
  site. It pairs with the `nightlabs.unifi.api.site` doc fragment, and the two are kept in step by
  hand.
- `_info` modules that use `site`, `device` or a similar option as an optional filter declare it
  inline instead, as `dict(type="str")`, and document it in the module itself.
- An identifier taken from the user and placed in a URL path is parsed with `uuid.UUID` first.
- Single-item endpoints return the object itself; `_info` modules wrap it in a one-element list so
  the return value is always a list.
- Every new module is added to the `unifi` action group in `meta/runtime.yml`.
