# -*- coding: utf-8 -*-
# Copyright: (c) 2026, John Cuckovich
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  host:
    description:
      - Hostname or IP address of the UniFi console (for example a UCG, UDM or Cloud Key).
      - Can also be set with the E(UNIFI_HOST) environment variable.
    type: str
    required: true
  port:
    description:
      - HTTPS port of the console.
    type: int
    default: 443
  api_key:
    description:
      - UniFi Network API key, created in the Network app under C(Settings > Control Plane > Integrations).
      - Can also be set with the E(UNIFI_API_KEY) environment variable.
    type: str
    required: true
  validate_certs:
    description:
      - Whether to verify the console's TLS certificate.
      - Set to V(false) for consoles using the factory self-signed certificate.
      - Can also be set with the E(UNIFI_VALIDATE_CERTS) environment variable.
    type: bool
    default: true
  timeout:
    description:
      - Request timeout in seconds.
    type: int
    default: 30
notes:
  - Uses the official UniFi Network Integration API (C(/proxy/network/integration/v1)).
"""

    # Used by modules that act on one site:
    #   extends_documentation_fragment:
    #     - nightlabs.unifi.api
    #     - nightlabs.unifi.api.site
    SITE = r"""
options:
  site:
    description:
      - The site to act on, given as its UUID, its internal reference, or its display name.
      - A value that parses as a UUID must match an existing site's UUID, in any letter case.
      - Any other value is matched against the site's C(internalReference) and C(name).
        Matching is exact and case-sensitive, so V(default) matches the internal reference of the
        default site and V(Default) matches its display name.
      - The task fails if no site matches.
      - The C(internalReference) never changes when a site is renamed, so prefer it over the display name in playbooks.
      - If the value matches more than one site (one site's internal reference equals another's name), the task fails; pass the UUID instead.
      - M(nightlabs.unifi.site_info) lists every site with its RV(nightlabs.unifi.site_info#module:sites[].id),
        RV(nightlabs.unifi.site_info#module:sites[].internalReference) and RV(nightlabs.unifi.site_info#module:sites[].name).
    type: str
    required: true
"""
