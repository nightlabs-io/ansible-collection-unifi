# -*- coding: utf-8 -*-
# Copyright: (c) 2026, John Cuckovich
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared client for the UniFi Network Integration API."""

from __future__ import annotations

import json
from uuid import UUID

from ansible.module_utils.basic import env_fallback
from ansible.module_utils.six.moves.urllib.parse import urlencode
from ansible.module_utils.urls import fetch_url

API_BASE = "/proxy/network/integration/v1"
PAGE_LIMIT = 200


def unifi_argument_spec():
    """Connection options shared by every module in the collection."""
    return dict(
        host=dict(type="str", required=True, fallback=(env_fallback, ["UNIFI_HOST"])),
        port=dict(type="int", default=443),
        api_key=dict(type="str", required=True, no_log=True, fallback=(env_fallback, ["UNIFI_API_KEY"])),
        validate_certs=dict(type="bool", default=True, fallback=(env_fallback, ["UNIFI_VALIDATE_CERTS"])),
        timeout=dict(type="int", default=30),
    )


# For modules that act on exactly one site, so the option is required. Pairs with the
# nightlabs.unifi.api.site doc fragment; keep the two in step. Modules that use `site`
# as an optional filter (site_info) declare it inline instead.
def unifi_site_argument_spec():
    """The required `site` option (UUID, internalReference or name)."""
    return dict(
        site=dict(type="str", required=True),
    )


class UnifiAPIError(Exception):
    pass


class UnifiNotFoundError(UnifiAPIError):
    pass


class UnifiClient:
    def __init__(self, module):
        self.module = module
        p = module.params
        self.base_url = "https://%s:%d%s" % (p["host"], p["port"], API_BASE)
        self.headers = {
            "X-API-KEY": p["api_key"],
            "Accept": "application/json",
        }
        # fetch_url reads validate_certs from module.params; the timeout is passed per call.
        self.timeout = p["timeout"]

    def request(self, path, method="GET", query=None, body=None):
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        headers = dict(self.headers)
        data = None
        if body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"

        resp, info = fetch_url(self.module, url, data=data, headers=headers, method=method, timeout=self.timeout)
        status = info.get("status", -1)
        raw = resp.read() if resp else info.get("body", b"")

        if status == -1:
            raise UnifiAPIError("Could not connect to %s: %s" % (url, info.get("msg")))
        if status == 401:
            raise UnifiAPIError("Authentication failed (HTTP 401): check api_key")
        if status == 404:
            raise UnifiNotFoundError("Resource not found (HTTP 404): %s" % url)
        if status >= 400:
            raise UnifiAPIError("HTTP %d from %s %s: %s" % (status, method, url, _to_text(raw)))

        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            raise UnifiAPIError("Non-JSON response from %s: %s" % (url, _to_text(raw)[:500]))

    def get_all(self, path, query=None):
        """GET a paginated collection endpoint and return every item in `data`."""
        items = []
        offset = 0
        while True:
            q = dict(query or {}, offset=offset, limit=PAGE_LIMIT)
            page = self.request(path, query=q) or {}
            batch = page.get("data", [])
            items.extend(batch)
            offset += len(batch)
            # Without a totalCount, keep paging until an empty page rather than stop after one.
            total = page.get("totalCount")
            if not batch or (total is not None and offset >= total):
                return items

    def resolve_site(self, site):
        """Resolve a site by its UUID, internal reference, or name, and return its UUID."""
        return self.get_site(site)["id"]

    def get_site(self, site):
        """Return the full site record for a UUID, internal reference, or name."""
        if not site:
            raise UnifiAPIError("site is required")

        # Consoles have a handful of sites, so matching locally costs one request
        # and avoids building filter strings, which break on quotes in names.
        sites = self.get_all("/sites")

        try:
            site_id = str(UUID(site))
        except ValueError:
            site_id = None

        if site_id:
            matches = [s for s in sites if s.get("id") == site_id]
        else:
            matches = [s for s in sites if site in (s.get("internalReference"), s.get("name"))]

        if not matches:
            raise UnifiAPIError("Could not resolve site: no site has UUID, internal reference or name '%s'" % site)
        if len(matches) > 1:
            raise UnifiAPIError("'%s' matches more than one site; use the site's UUID" % site)
        return matches[0]

    def resolve_policy(self, site_id, record_type, domain, identity=None, case_sensitive=()):
        """Return the DNS policy that is one record, or None if there isn't one.

        A record is its type, its domain and `identity`: the API fields that tell apart
        records of one type on one domain (an MX record's mail server, for example).
        Values compare case-insensitively, as DNS names do, except the API fields named
        in `case_sensitive`.
        """

        if not site_id:
            raise UnifiAPIError("No site specified")
        if not domain:
            raise UnifiAPIError("No domain specified")

        wanted = dict(identity or {}, domain=domain)

        def same(key, stored, value):
            if key not in case_sensitive and isinstance(stored, str) and isinstance(value, str):
                return stored.lower() == value.lower()
            return stored == value

        policies = self.get_all("/sites/%s/dns/policies" % site_id)
        matches = [
            p for p in policies
            if p.get("type") == record_type and all(same(k, p.get(k), v) for k, v in wanted.items())
        ]

        if not matches:
            return None
        if len(matches) > 1:
            raise UnifiAPIError("%s %s matches more than one DNS policy on site %s; remove the duplicate"
                                % (record_type, ", ".join("%s=%s" % kv for kv in sorted(wanted.items())), site_id))
        return matches[0]


def _to_text(raw):
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)
